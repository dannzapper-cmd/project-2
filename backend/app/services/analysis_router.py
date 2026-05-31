import logging
import time

from app.config import Settings
from app.schemas import AnalyzeImageResponse, GroundingResult
from app.services.gemini_analysis import (
    GeminiAnalysisError,
    analyze_image_with_gemini,
)
from app.services.mock_analysis import build_mock_image_analysis_response
from app.services.openfoodfacts import OpenFoodFactsClient


logger = logging.getLogger(__name__)


class AnalysisUnavailableError(Exception):
    def __init__(
        self,
        *,
        error: str,
        message: str,
        latency_ms: int,
        status_code: int = 503,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.latency_ms = latency_ms
        self.status_code = status_code


def _latency_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _merge_grounding(
    response: AnalyzeImageResponse, grounding: GroundingResult
) -> AnalyzeImageResponse:
    response.grounding_status = grounding.grounding_status
    response.grounding_summary = grounding.grounding_summary
    response.match_method = grounding.match_method
    response.source_product_id = grounding.source_product_id
    response.retrieved_at = grounding.retrieved_at
    response.citations = grounding.citations
    response.source_trace = grounding.source_trace
    response.product_enrichment = grounding.product_enrichment
    return response


async def _ground_response(response: AnalyzeImageResponse) -> AnalyzeImageResponse:
    if response.mode not in {"gemini", "mock"}:
        return response

    # Privacy: grounding data is merged in-memory and not persisted beyond this request.
    grounding = await OpenFoodFactsClient().ground(response.product)
    return _merge_grounding(response, grounding)

async def analyze_product_image(
    *,
    request_id: str,
    image_bytes: bytes,
    content_type: str,
    started_at: float,
    api_version: str,
    settings: Settings,
) -> AnalyzeImageResponse:
    if settings.analysis_mode == "mock":
        response = build_mock_image_analysis_response(
            request_id=request_id,
            latency_ms=_latency_ms(started_at),
            api_version=api_version,
            mode="mock",
        )
        return await _ground_response(response)

    if not settings.gemini_api_key:
        logger.warning(
            "Gemini mode requested without API key",
            extra={"request_id": request_id, "mode": "error"},
        )
        raise AnalysisUnavailableError(
            error="gemini_not_configured",
            message="Gemini API key is not configured.",
            latency_ms=0,
        )

    try:
        response = await analyze_image_with_gemini(
            request_id=request_id,
            image_bytes=image_bytes,
            content_type=content_type,
            settings=settings,
            latency_ms=_latency_ms(started_at),
            api_version=api_version,
        )
        response.meta.latency_ms = _latency_ms(started_at)
        return await _ground_response(response)
    except GeminiAnalysisError as exc:
        logger.warning(
            "Gemini analysis failed",
            extra={
                "request_id": request_id,
                "mode": "mock_fallback"
                if settings.mock_fallback_allowed
                else "error",
                "model": settings.gemini_model,
                "error_class": exc.error_class,
            },
        )

        if settings.mock_fallback_allowed:
            return build_mock_image_analysis_response(
                request_id=request_id,
                latency_ms=_latency_ms(started_at),
                api_version=api_version,
                mode="mock_fallback",
                warnings=[
                    "Gemini unavailable. Showing mock result.",
                    "No image was stored.",
                ],
            )

        raise AnalysisUnavailableError(
            error="gemini_unavailable",
            message="Gemini analysis failed and mock fallback is disabled.",
            latency_ms=_latency_ms(started_at),
        )
