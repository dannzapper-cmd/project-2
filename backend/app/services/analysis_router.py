import logging
import time

from app.config import Settings
from app.schemas import AnalyzeImageResponse, GroundingResult
from app.services.analysis_cache import analysis_cache, compute_cache_key
from app.services.gemini_analysis import (
    GeminiAnalysisError,
    analyze_image_with_gemini,
)
from app.services.metrics import GROUNDING_COUNTERS, metrics
from app.services.mock_analysis import build_mock_image_analysis_response
from app.services.openfoodfacts import OpenFoodFactsClient


logger = logging.getLogger(__name__)

# Only real analysis results are cached. Fallback results are intentionally not
# cached so a transient Gemini outage cannot pin a mock result for the full TTL.
CACHEABLE_MODES = {"mock", "gemini"}


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
    merged = _merge_grounding(response, grounding)
    counter = GROUNDING_COUNTERS.get(merged.grounding_status)
    if counter:
        await metrics.increment(counter)
    return merged


def _model_version(settings: Settings) -> str:
    return settings.gemini_model if settings.analysis_mode == "gemini" else "mock"


async def _run_analysis(
    *,
    request_id: str,
    image_bytes: bytes,
    content_type: str,
    started_at: float,
    api_version: str,
    settings: Settings,
) -> AnalyzeImageResponse:
    if settings.analysis_mode == "mock":
        await metrics.increment("mock_requests")
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
        await metrics.increment("analysis_errors")
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
        await metrics.increment("gemini_requests")
        return await _ground_response(response)
    except GeminiAnalysisError as exc:
        logger.warning(
            "Gemini analysis failed request_id=%s model=%s error_class=%s "
            "provider_status=%s provider_code=%s safe_message=%s",
            request_id,
            settings.gemini_model,
            exc.error_class,
            exc.status_code,
            exc.code,
            exc.safe_message,
            extra={
                "request_id": request_id,
                "mode": "mock_fallback"
                if settings.mock_fallback_allowed
                else "error",
                "model": settings.gemini_model,
                "error_class": exc.error_class,
                "safe_message": exc.safe_message,
                "provider_status": exc.status_code,
                "provider_code": exc.code,
            },
        )

        if settings.mock_fallback_allowed:
            await metrics.increment("mock_fallbacks")
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

        await metrics.increment("analysis_errors")
        raise AnalysisUnavailableError(
            error="gemini_unavailable",
            message="Gemini analysis failed and mock fallback is disabled.",
            latency_ms=_latency_ms(started_at),
        )


async def analyze_product_image(
    *,
    request_id: str,
    image_bytes: bytes,
    content_type: str,
    started_at: float,
    api_version: str,
    settings: Settings,
) -> AnalyzeImageResponse:
    await metrics.increment("total_analysis_requests")

    cache_key: str | None = None
    if settings.cache_enabled:
        # Privacy: image bytes are hashed for cache keys but never logged or
        # persisted. The cache value is the analysis response object only.
        cache_key = compute_cache_key(
            image_bytes,
            analysis_mode=settings.analysis_mode,
            model_version=_model_version(settings),
        )
        try:
            cached = await analysis_cache.get(cache_key)
        except Exception:  # noqa: BLE001
            # A cache failure must never break analysis; fall through to a
            # normal run as if it were a miss.
            logger.warning("Analysis cache lookup failed", extra={"mode": "cache"})
            cached = None

        if cached is not None:
            await metrics.increment("cache_hits")
            cached.request_id = request_id
            cached.meta.latency_ms = _latency_ms(started_at)
            cached.cache_hit = True
            await metrics.record_latency(cached.meta.latency_ms)
            return cached

        await metrics.increment("cache_misses")

    response = await _run_analysis(
        request_id=request_id,
        image_bytes=image_bytes,
        content_type=content_type,
        started_at=started_at,
        api_version=api_version,
        settings=settings,
    )

    # cache_hit=False on a fresh run when caching is on; None when disabled.
    response.cache_hit = False if settings.cache_enabled else None
    await metrics.record_latency(response.meta.latency_ms)

    # Never cache errors (errors raise above) or fallback results.
    if cache_key is not None and response.mode in CACHEABLE_MODES:
        try:
            await analysis_cache.set(
                cache_key,
                response,
                ttl_seconds=settings.cache_ttl_seconds,
                max_entries=settings.cache_max_entries,
            )
        except Exception:  # noqa: BLE001
            logger.warning("Analysis cache store failed", extra={"mode": "cache"})

    return response
