import logging
import time

from app.config import get_effective_analysis_mode, get_settings
from app.schemas import AnalyzeImageResponse
from app.services.gemini_analysis import (
    GeminiAnalysisError,
    analyze_image_with_gemini,
)
from app.services.mock_analysis import build_mock_image_analysis_response


logger = logging.getLogger(__name__)


def _latency_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


async def analyze_product_image(
    *,
    request_id: str,
    image_bytes: bytes,
    content_type: str,
    started_at: float,
    api_version: str,
) -> AnalyzeImageResponse:
    settings = get_settings()
    effective_mode = get_effective_analysis_mode(settings)

    if settings.analysis_mode == "gemini" and not settings.gemini_api_key:
        logger.warning(
            "Gemini mode requested without API key",
            extra={"request_id": request_id, "mode": "mock_fallback"},
        )
        return build_mock_image_analysis_response(
            request_id=request_id,
            latency_ms=_latency_ms(started_at),
            api_version=api_version,
            mode="mock_fallback",
            warnings=[
                "Analysis mode is set to 'gemini' but GEMINI_API_KEY is not "
                "configured. Returning mock response.",
                "No image was stored.",
            ],
        )

    if effective_mode == "mock":
        warnings = None
        if not settings.analysis_mode and not settings.gemini_api_key:
            warnings = [
                "AI analysis is not configured. Returning mock response.",
                "No image was stored.",
            ]

        return build_mock_image_analysis_response(
            request_id=request_id,
            latency_ms=_latency_ms(started_at),
            api_version=api_version,
            mode="mock",
            warnings=warnings,
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
        return response
    except GeminiAnalysisError as exc:
        logger.warning(
            "Gemini analysis failed",
            extra={
                "request_id": request_id,
                "mode": "mock_fallback",
                "model": settings.gemini_model,
                "error_class": exc.error_class,
            },
        )
        return build_mock_image_analysis_response(
            request_id=request_id,
            latency_ms=_latency_ms(started_at),
            api_version=api_version,
            mode="mock_fallback",
            warnings=[
                "Analysis could not be completed. Using fallback response.",
                "No image was stored.",
            ],
        )
