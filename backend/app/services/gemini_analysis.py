import asyncio
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


class GeminiAnalysisError(Exception):
    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class


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


class GeminiProductResponse(BaseModel):
    product: GeminiProduct
    insights: list[GeminiInsight] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)


GEMINI_IMAGE_ANALYSIS_INSTRUCTION = """
Analyze the product image and return structured output only.

Rules:
- Identify visible product information from the packaging or label.
- Extract likely display_name, category, and brand only when visible or reasonably supported.
- Extract visible attributes from the package or label only when reasonably supported.
- Provide concise, actionable insights.
- Provide warnings or limitations when uncertain.
- Provide confidence score from 0.0 to 1.0 and label low, medium, or high.
- Never claim authenticity or fake-product detection.
- Never scrape, estimate, or claim live prices.
- Never make medical diagnoses.
- Never make absolute health claims.
- For food or CPG, describe visible packaging or label clues only. Do not claim
  nutritional or allergen facts unless they are visible in the image.
- If the product is unclear, use low confidence and ask for a better photo.
- Do not include citations. Retrieval-backed citations are not connected yet.
"""


def _parse_gemini_response(response: object) -> GeminiProductResponse:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, GeminiProductResponse):
        return parsed
    if parsed is not None:
        return GeminiProductResponse.model_validate(parsed)

    text = getattr(response, "text", None)
    if not text:
        raise GeminiAnalysisError("EmptyGeminiResponse")

    return GeminiProductResponse.model_validate_json(text)


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
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=content_type,
        )
        text_part = types.Part.from_text(text=GEMINI_IMAGE_ANALYSIS_INSTRUCTION)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiProductResponse,
            max_output_tokens=1024,
            temperature=0.1,
        )

        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model,
                contents=[image_part, text_part],
                config=config,
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
        parsed = _parse_gemini_response(response)
    except asyncio.TimeoutError as exc:
        raise GeminiAnalysisError("TimeoutError") from exc
    except (ValidationError, ValueError, TypeError) as exc:
        raise GeminiAnalysisError(exc.__class__.__name__) from exc
    except Exception as exc:
        raise GeminiAnalysisError(exc.__class__.__name__) from exc

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
