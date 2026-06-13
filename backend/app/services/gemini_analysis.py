import asyncio
import logging
import re
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.schemas import (
    AnalyzeImageResponse,
    Confidence,
    Insight,
    PrivacySummary,
    ProductSummary,
    ResponseMeta,
)


GEMINI_TIMEOUT_SECONDS = 30.0
GEMINI_MAX_OUTPUT_TOKENS = 4096
GEMINI_MAX_PARSE_ATTEMPTS = 3
SAFE_MESSAGE_MAX_CHARS = 300
INVALID_STRUCTURED_JSON_SAFE_MESSAGE = (
    "Gemini returned invalid structured JSON after retries."
)

_API_KEY_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|x-goog-api-key)\b\s*[:=]\s*([^\s,;]+)"
)
_FENCED_JSON_PATTERN = re.compile(
    r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.IGNORECASE | re.DOTALL
)
_DATA_IMAGE_PATTERN = re.compile(
    r"(?i)data:image/[a-z0-9.+-]+;base64,[a-z0-9+/=\s]+"
)
_LONG_BASE64_CHUNK_PATTERN = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/=]{80,}")
_BYTES_LITERAL_PATTERN = re.compile(r"b(['\"]).*?\1", re.DOTALL)
_SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?i)\b(prompt|payload|request_payload|contents|response_body|image_bytes)\b\s*[:=]\s*([^;,\n]+)"
)
logger = logging.getLogger(__name__)


class GeminiAnalysisError(Exception):
    def __init__(
        self,
        error_class: str,
        *,
        safe_message: str | None = None,
        status_code: int | None = None,
        code: str | int | None = None,
    ) -> None:
        super().__init__(error_class)
        self.error_class = error_class
        self.safe_message = _truncate_safe_message(safe_message)
        self.status_code = status_code
        self.code = code


def _truncate_safe_message(message: str | None) -> str | None:
    if not message:
        return None
    normalized = " ".join(message.split())
    if not normalized:
        return None
    return normalized[:SAFE_MESSAGE_MAX_CHARS]


def _sanitize_exception_message(
    message: str | None, *, api_key: str | None
) -> str | None:
    if not message:
        return None

    safe_message = message
    safe_message = _DATA_IMAGE_PATTERN.sub("[REDACTED_IMAGE_DATA]", safe_message)
    safe_message = _BYTES_LITERAL_PATTERN.sub("b'[REDACTED_BYTES]'", safe_message)
    safe_message = _API_KEY_PATTERN.sub(r"\1=[REDACTED]", safe_message)
    safe_message = _SENSITIVE_FIELD_PATTERN.sub(r"\1=[REDACTED]", safe_message)
    safe_message = safe_message.replace("image_bytes", "[REDACTED_IMAGE_BYTES]")
    safe_message = _LONG_BASE64_CHUNK_PATTERN.sub("[REDACTED_BASE64]", safe_message)

    if api_key:
        safe_message = safe_message.replace(api_key, "[REDACTED_API_KEY]")

    return _truncate_safe_message(safe_message)


def _coerce_status_code(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _extract_provider_details(exc: Exception) -> tuple[int | None, str | int | None]:
    status_code = _coerce_status_code(getattr(exc, "status_code", None))
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = _coerce_status_code(getattr(response, "status_code", None))

    code = getattr(exc, "code", None)
    if isinstance(code, bool) or not isinstance(code, (str, int)):
        code = None

    return status_code, code


def _gemini_analysis_error_from_exception(
    exc: Exception, *, api_key: str | None
) -> GeminiAnalysisError:
    status_code, code = _extract_provider_details(exc)
    return GeminiAnalysisError(
        exc.__class__.__name__,
        safe_message=_sanitize_exception_message(str(exc), api_key=api_key),
        status_code=status_code,
        code=code,
    )


class GeminiConfidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    label: Literal["low", "medium", "high"]


class GeminiInsight(BaseModel):
    title: str
    body: str
    type: str = "observation"


class GeminiProduct(BaseModel):
    display_name: str
    category: str
    brand: str | None = None
    detected_attributes: list[str] = Field(default_factory=list)
    confidence: GeminiConfidence
    barcode: str | None = Field(
        default=None,
        description="EAN-13, UPC-A, or similar if clearly visible in image.",
    )


class GeminiProductResponse(BaseModel):
    product: GeminiProduct
    insights: list[GeminiInsight] = Field(default_factory=list, max_length=3)
    warnings: list[str] = Field(default_factory=list, max_length=3)
    next_questions: list[str] = Field(default_factory=list, max_length=3)


GEMINI_IMAGE_ANALYSIS_INSTRUCTION = """
Analyze the product image and return structured output only.

Rules:
- Identify visible product information from the packaging or label.
- Extract likely display_name, category, and brand only when visible or reasonably supported.
- Extract visible attributes from the package or label only when reasonably supported.
- Extract barcode only when an EAN-13, UPC-A, or similar code is clearly visible.
- Provide concise, actionable insights.
- Keep insights concise; return at most 3 insights, each no more than one short sentence.
- Provide at most 3 warnings or limitations when uncertain.
- Provide at most 3 next_questions.
- Provide confidence score from 0.0 to 1.0 and label low, medium, or high.
- Return JSON only. Do not include markdown, comments, prose, or code fences.
- Never claim authenticity or fake-product detection.
- Never scrape, estimate, or claim live prices.
- Never make medical diagnoses.
- Never make absolute health claims.
- For food or CPG, describe visible packaging or label clues only. Do not claim
  nutritional or allergen facts unless they are visible in the image.
- If the product is unclear, use low confidence and ask for a better photo.
- Do not include citations. Retrieval-backed citations are not connected yet.
"""


def _normalize_response_text(text: str) -> str:
    stripped = text.strip()
    fenced_match = _FENCED_JSON_PATTERN.match(stripped)
    if fenced_match:
        return fenced_match.group(1).strip()
    return stripped


def _parse_gemini_response(response: object) -> GeminiProductResponse:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, GeminiProductResponse):
        return parsed
    if parsed is not None:
        return GeminiProductResponse.model_validate(parsed)

    text = getattr(response, "text", None)
    if not text:
        raise GeminiAnalysisError(
            "EmptyGeminiResponse",
            safe_message="Gemini returned an empty response.",
        )

    normalized_text = _normalize_response_text(text)
    if not normalized_text:
        raise GeminiAnalysisError(
            "EmptyGeminiResponse",
            safe_message="Gemini returned an empty response.",
        )

    return GeminiProductResponse.model_validate_json(normalized_text)


def _is_retriable_parse_failure(exc: Exception) -> bool:
    status_code, code = _extract_provider_details(exc)
    return status_code is None and code is None


def _log_parse_retry(
    *,
    request_id: str,
    model: str,
    attempt: int,
    exc: Exception,
) -> None:
    error_class = (
        exc.error_class
        if isinstance(exc, GeminiAnalysisError)
        else exc.__class__.__name__
    )
    logger.warning(
        "Gemini structured JSON parse failed; retrying "
        "request_id=%s model=%s attempt=%s error_class=%s",
        request_id,
        model,
        attempt,
        error_class,
        extra={
            "request_id": request_id,
            "model": model,
            "attempt": attempt,
            "error_class": error_class,
        },
    )


async def _generate_and_parse_with_retries(
    *,
    client: genai.Client,
    request_id: str,
    model: str,
    contents: list[types.Part],
    config: types.GenerateContentConfig,
) -> GeminiProductResponse:
    last_parse_exc: Exception | None = None
    parse_error_types = (ValidationError, ValueError, TypeError, GeminiAnalysisError)

    for attempt in range(1, GEMINI_MAX_PARSE_ATTEMPTS + 1):
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=contents,
                config=config,
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )

        try:
            return _parse_gemini_response(response)
        except parse_error_types as exc:
            if not _is_retriable_parse_failure(exc):
                raise

            last_parse_exc = exc
            if attempt >= GEMINI_MAX_PARSE_ATTEMPTS:
                break

            _log_parse_retry(
                request_id=request_id,
                model=model,
                attempt=attempt,
                exc=exc,
            )

    raise GeminiAnalysisError(
        "InvalidGeminiStructuredJson",
        safe_message=INVALID_STRUCTURED_JSON_SAFE_MESSAGE,
    ) from last_parse_exc


async def analyze_image_with_gemini(
    *,
    request_id: str,
    image_bytes: bytes,
    content_type: str,
    settings: Settings,
    latency_ms: int,
    api_version: str,
) -> AnalyzeImageResponse:
    if not settings.gemini_api_key:
        raise GeminiAnalysisError("MissingGeminiApiKey")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        # Privacy: image bytes are not logged or persisted.
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=content_type,
        )
        text_part = types.Part.from_text(text=GEMINI_IMAGE_ANALYSIS_INSTRUCTION)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiProductResponse,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            temperature=0.1,
        )

        parsed = await _generate_and_parse_with_retries(
            client=client,
            request_id=request_id,
            model=settings.gemini_model,
            contents=[image_part, text_part],
            config=config,
        )
    except asyncio.TimeoutError as exc:
        raise _gemini_analysis_error_from_exception(
            exc, api_key=settings.gemini_api_key
        ) from exc
    except (ValidationError, ValueError, TypeError) as exc:
        raise _gemini_analysis_error_from_exception(
            exc, api_key=settings.gemini_api_key
        ) from exc
    except GeminiAnalysisError:
        raise
    except Exception as exc:
        raise _gemini_analysis_error_from_exception(
            exc, api_key=settings.gemini_api_key
        ) from exc

    warnings = parsed.warnings or [
        "No RAG or retrieval-backed citations are connected yet.",
    ]

    return AnalyzeImageResponse(
        request_id=request_id,
        mode="gemini",
        status="completed",
        product=ProductSummary(
            display_name=parsed.product.display_name,
            category=parsed.product.category,
            brand=parsed.product.brand,
            detected_attributes=parsed.product.detected_attributes,
            confidence=Confidence(
                score=parsed.product.confidence.score,
                label=parsed.product.confidence.label,
            ),
            barcode=parsed.product.barcode,
        ),
        insights=[
            Insight(title=insight.title, body=insight.body, type=insight.type)
            for insight in parsed.insights
        ],
        warnings=warnings,
        citations=[],
        next_questions=parsed.next_questions
        or [
            "Would you like a clearer product identification?",
            "What would you like to know about this product?",
        ],
        privacy=PrivacySummary(image_stored=False, image_retention="none"),
        meta=ResponseMeta(
            model=settings.gemini_model,
            latency_ms=latency_ms,
            api_version=api_version,
        ),
    )
