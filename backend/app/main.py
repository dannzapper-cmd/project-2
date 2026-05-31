import logging
import os
import time
import uuid

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import ConfigurationError, get_effective_analysis_mode, get_settings
from app.schemas import (
    AnalyzeImageResponse,
    CompareProductsRequest,
    CompareProductsResponse,
    HealthResponse,
    MetricsSummaryResponse,
    ProductChatRequest,
    ProductChatResponse,
    ProductGraphRequest,
    ProductGraphResponse,
)
from app.services.analysis_router import (
    AnalysisUnavailableError,
    analyze_product_image,
)
from app.services.llmops import llmops
from app.services.metrics import metrics
from app.services.product_chat import ProductChatError, answer_product_question
from app.services.product_compare import ProductCompareError, compare_products
from app.services.product_graph import build_product_graph_response


SERVICE_NAME = "snapinsight-backend"
APP_VERSION = "0.1.0"
API_VERSION = "v1"
# User-friendly message kept stable for both 413 oversized uploads and the UI.
OVERSIZED_IMAGE_MESSAGE = "Image is too large. Please upload a smaller image."
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
logger = logging.getLogger(__name__)


def get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("SNAPINSIGHT_ALLOWED_ORIGINS")
    if not raw_origins:
        return DEFAULT_ALLOWED_ORIGINS

    origins = [
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    ]
    return origins or DEFAULT_ALLOWED_ORIGINS


def latency_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def llmops_status_fields() -> dict[str, str | bool | None]:
    return llmops.status.api_fields()


def trace_backend_event(name: str, metadata: dict) -> None:
    metadata.setdefault("app_version", APP_VERSION)
    llmops.trace_event(name=name, metadata=metadata)


def build_error_response(
    *,
    status_code: int,
    error: str,
    message: str,
    request_id: str,
    latency_ms: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "mode": "error",
            "message": message,
            "request_id": request_id,
            "latency_ms": latency_ms,
        },
    )


def build_chat_error_response(
    *,
    status_code: int,
    error: str,
    message: str,
    request_id: str,
    latency_ms: int | None = None,
) -> JSONResponse:
    content = {
        "error": error,
        "message": message,
        "mode": "error",
        "request_id": request_id,
    }
    if latency_ms is not None:
        content["latency_ms"] = latency_ms
    return JSONResponse(status_code=status_code, content=content)


def build_compare_error_response(
    *,
    status_code: int,
    error: str,
    message: str,
    request_id: str,
    latency_ms: int | None = None,
) -> JSONResponse:
    content = {
        "error": error,
        "message": message,
        "request_id": request_id,
    }
    if latency_ms is not None:
        content["latency_ms"] = latency_ms
    return JSONResponse(status_code=status_code, content=content)


def _contains_media_payload(value: object) -> bool:
    forbidden_keys = {
        "image",
        "image_bytes",
        "image_base64",
        "base64",
        "audio",
        "audio_bytes",
        "audio_base64",
    }
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in forbidden_keys:
                return True
            if _contains_media_payload(nested):
                return True
    if isinstance(value, list):
        return any(_contains_media_payload(item) for item in value)
    return False


app = FastAPI(
    title="SnapInsight Backend API",
    description="SnapInsight image analysis API with mock and Gemini modes.",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_llmops() -> None:
    llmops.refresh_from_env()


@app.on_event("shutdown")
async def shutdown_llmops() -> None:
    llmops.shutdown()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        llmops_fields = llmops_status_fields()
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": SERVICE_NAME,
                "mode": "error",
                "version": APP_VERSION,
                "analysis_mode": "invalid",
                "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
                "mock_fallback_allowed": False,
                "message": exc.message,
                **llmops_fields,
            },
        )

    analysis_mode = get_effective_analysis_mode(settings)
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        mode=analysis_mode,
        version=APP_VERSION,
        analysis_mode=analysis_mode,
        gemini_configured=bool(settings.gemini_api_key),
        mock_fallback_allowed=settings.mock_fallback_allowed,
        cache_enabled=settings.cache_enabled,
        **llmops_status_fields(),
    )


@app.post("/v1/graph/product", response_model=ProductGraphResponse)
async def graph_product(
    request: ProductGraphRequest,
) -> ProductGraphResponse | JSONResponse:
    start_time = time.monotonic()
    request_id = str(uuid.uuid4())

    try:
        settings = get_settings()
    except ConfigurationError as exc:
        trace_backend_event(
            "snapinsight.graph",
            {
                "route": "/v1/graph/product",
                "operation": "graph_product",
                "status": "error",
                "status_code": 500,
                "error_type": "invalid_configuration",
                "latency_ms": latency_ms(start_time),
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "invalid_configuration",
                "message": exc.message,
                "request_id": request_id,
            },
        )

    if _contains_media_payload(request.model_dump()):
        trace_backend_event(
            "snapinsight.graph",
            {
                "route": "/v1/graph/product",
                "operation": "graph_product",
                "status": "error",
                "status_code": 400,
                "error_type": "graph_media_not_allowed",
                "latency_ms": latency_ms(start_time),
            },
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "graph_media_not_allowed",
                "message": "Graph accepts analysis results only, not image or audio bytes.",
                "request_id": request_id,
            },
        )

    try:
        response = build_product_graph_response(
            analysis=request.analysis,
            request_id=request_id,
            settings=settings,
            started_at=start_time,
        )
        trace_backend_event(
            "snapinsight.graph",
            {
                "route": "/v1/graph/product",
                "operation": "graph_product",
                "status": "ok",
                "status_code": 200,
                "graph_backend": response.graph_backend,
                "graph_enabled": response.graph_enabled,
                "node_count": len(response.nodes),
                "edge_count": len(response.edges),
                "evidence_paths_count": len(response.evidence_paths),
                "latency_ms": response.latency_ms,
            },
        )
        return response
    except ValueError as exc:
        trace_backend_event(
            "snapinsight.graph",
            {
                "route": "/v1/graph/product",
                "operation": "graph_product",
                "status": "error",
                "status_code": 400,
                "error_type": "graph_invalid_payload",
                "latency_ms": latency_ms(start_time),
            },
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "graph_invalid_payload",
                "message": str(exc),
                "request_id": request_id,
            },
        )


@app.get("/v1/metrics/summary", response_model=MetricsSummaryResponse)
async def metrics_summary() -> MetricsSummaryResponse:
    # SECURITY NOTE: This endpoint is intentionally unauthenticated
    # for demo and operational visibility purposes.
    # In a production deployment with real users, this endpoint
    # should be protected or rate-limited.
    # Auth and rate limiting are deferred to Block 14/15.
    snapshot = await metrics.summary()
    snapshot.update(llmops_status_fields())
    return MetricsSummaryResponse(**snapshot)


@app.post("/v1/analyze/image", response_model=AnalyzeImageResponse)
async def analyze_image(
    file: UploadFile = File(...),
) -> AnalyzeImageResponse | JSONResponse:
    start_time = time.monotonic()
    request_id = str(uuid.uuid4())

    try:
        settings = get_settings()
    except ConfigurationError as exc:
        elapsed_ms = latency_ms(start_time)
        trace_backend_event(
            "snapinsight.analyze",
            {
                "route": "/v1/analyze/image",
                "operation": "analyze_image",
                "analysis_mode": "error",
                "status": "error",
                "status_code": 500,
                "error_type": "invalid_analysis_mode",
                "latency_ms": elapsed_ms,
            },
        )
        return build_error_response(
            status_code=500,
            error="invalid_analysis_mode",
            message=exc.message,
            request_id=request_id,
            latency_ms=elapsed_ms,
        )

    content_type = file.content_type or ""

    # This MIME type is client-declared and not verified against file magic
    # bytes yet. Magic byte validation is a future hardening step.
    if not content_type.startswith("image/"):
        trace_backend_event(
            "snapinsight.analyze",
            {
                "route": "/v1/analyze/image",
                "operation": "analyze_image",
                "analysis_mode": settings.analysis_mode,
                "status": "error",
                "status_code": 400,
                "error_type": "unsupported_file_type",
                "latency_ms": latency_ms(start_time),
            },
        )
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload an image/* file.",
        )

    try:
        contents = await file.read()
    finally:
        await file.close()

    file_size_bytes = len(contents)
    max_image_bytes = settings.max_image_mb * 1024 * 1024
    if file_size_bytes > max_image_bytes:
        # Privacy: reject oversized uploads before any analysis or caching so
        # large image bytes are never hashed, processed, or retained.
        trace_backend_event(
            "snapinsight.analyze",
            {
                "route": "/v1/analyze/image",
                "operation": "analyze_image",
                "analysis_mode": settings.analysis_mode,
                "status": "error",
                "status_code": 413,
                "error_type": "oversized_image",
                "latency_ms": latency_ms(start_time),
            },
        )
        raise HTTPException(
            status_code=413,
            detail=OVERSIZED_IMAGE_MESSAGE,
        )

    # Privacy: image bytes are hashed for cache keys but never logged or persisted.
    logger.info(
        "Image analysis request accepted",
        extra={
            "request_id": request_id,
            "content_type": content_type,
            "file_size_bytes": file_size_bytes,
        },
    )

    try:
        response = await analyze_product_image(
            request_id=request_id,
            image_bytes=contents,
            content_type=content_type,
            started_at=start_time,
            api_version=API_VERSION,
            settings=settings,
        )
        trace_backend_event(
            "snapinsight.analyze",
            {
                "route": "/v1/analyze/image",
                "operation": "analyze_image",
                "analysis_mode": response.mode,
                "model_name": response.meta.model,
                "cache_hit": response.cache_hit,
                "grounding_status": response.grounding_status,
                "citations_count": len(response.citations),
                "warnings_count": len(response.warnings),
                "fallback_used": response.mode == "mock_fallback",
                "status": "ok",
                "status_code": 200,
                "latency_ms": response.meta.latency_ms,
            },
        )
        return response
    except AnalysisUnavailableError as exc:
        trace_backend_event(
            "snapinsight.analyze",
            {
                "route": "/v1/analyze/image",
                "operation": "analyze_image",
                "analysis_mode": "error",
                "model_name": settings.gemini_model,
                "status": "error",
                "status_code": exc.status_code,
                "error_type": exc.error,
                "latency_ms": exc.latency_ms,
            },
        )
        return build_error_response(
            status_code=exc.status_code,
            error=exc.error,
            message=exc.message,
            request_id=request_id,
            latency_ms=exc.latency_ms,
        )


@app.post("/v1/chat/product", response_model=ProductChatResponse)
async def chat_product(
    request: ProductChatRequest,
) -> ProductChatResponse | JSONResponse:
    start_time = time.monotonic()
    request_id = str(uuid.uuid4())
    # Operational counter only: no chat message content is recorded.
    await metrics.increment("chat_requests")

    try:
        settings = get_settings()
    except ConfigurationError as exc:
        elapsed_ms = latency_ms(start_time)
        trace_backend_event(
            "snapinsight.chat",
            {
                "route": "/v1/chat/product",
                "operation": "chat_product",
                "analysis_mode": "error",
                "chat_used": True,
                "status": "error",
                "status_code": 500,
                "error_type": "invalid_analysis_mode",
                "message_count": len(request.messages),
                "question_length": len(request.question),
                "has_product_context": request.analysis is not None,
                "latency_ms": elapsed_ms,
            },
        )
        return build_chat_error_response(
            status_code=500,
            error="invalid_analysis_mode",
            message=exc.message,
            request_id=request_id,
            latency_ms=elapsed_ms,
        )

    try:
        response = await answer_product_question(
            request_id=request_id,
            analysis=request.analysis,
            messages=request.messages,
            question=request.question,
            settings=settings,
            started_at=start_time,
        )
        trace_backend_event(
            "snapinsight.chat",
            {
                "route": "/v1/chat/product",
                "operation": "chat_product",
                "analysis_mode": response.mode,
                "model_name": settings.gemini_model if response.mode == "gemini" else "mock",
                "chat_used": True,
                "status": "ok",
                "status_code": 200,
                "message_count": len(request.messages),
                "question_length": len(request.question),
                "has_product_context": request.analysis is not None,
                "citations_count": len(response.citations_used),
                "warnings_count": len(response.warnings),
                "fallback_used": response.mode == "mock_fallback",
                "latency_ms": response.latency_ms,
            },
        )
        return response
    except ProductChatError as exc:
        trace_backend_event(
            "snapinsight.chat",
            {
                "route": "/v1/chat/product",
                "operation": "chat_product",
                "analysis_mode": "error",
                "chat_used": True,
                "status": "error",
                "status_code": exc.status_code,
                "error_type": exc.error,
                "message_count": len(request.messages),
                "question_length": len(request.question),
                "has_product_context": request.analysis is not None,
                "latency_ms": exc.latency_ms,
            },
        )
        return build_chat_error_response(
            status_code=exc.status_code,
            error=exc.error,
            message=exc.message,
            request_id=request_id,
            latency_ms=exc.latency_ms,
        )


@app.post("/v1/compare/products", response_model=CompareProductsResponse)
async def compare_product_results(
    payload: dict | None = Body(default=None),
) -> CompareProductsResponse | JSONResponse:
    start_time = time.monotonic()
    request_id = str(uuid.uuid4())
    # Operational counter only: no compared product data is recorded.
    await metrics.increment("compare_requests")

    if not payload or not payload.get("product_a") or not payload.get("product_b"):
        elapsed_ms = latency_ms(start_time)
        trace_backend_event(
            "snapinsight.compare",
            {
                "route": "/v1/compare/products",
                "operation": "compare_products",
                "compare_used": True,
                "status": "error",
                "status_code": 400,
                "error_type": "compare_missing_product",
                "fields_count": len(payload or {}),
                "latency_ms": elapsed_ms,
            },
        )
        return build_compare_error_response(
            status_code=400,
            error="compare_missing_product",
            message="Both Product A and Product B are required.",
            request_id=request_id,
            latency_ms=elapsed_ms,
        )

    if _contains_media_payload(payload):
        elapsed_ms = latency_ms(start_time)
        trace_backend_event(
            "snapinsight.compare",
            {
                "route": "/v1/compare/products",
                "operation": "compare_products",
                "compare_used": True,
                "status": "error",
                "status_code": 400,
                "error_type": "compare_media_not_allowed",
                "fields_count": len(payload),
                "latency_ms": elapsed_ms,
            },
        )
        return build_compare_error_response(
            status_code=400,
            error="compare_media_not_allowed",
            message="Compare accepts analysis results only, not image or audio bytes.",
            request_id=request_id,
            latency_ms=elapsed_ms,
        )

    try:
        request = CompareProductsRequest.model_validate(payload)
    except ValidationError:
        elapsed_ms = latency_ms(start_time)
        trace_backend_event(
            "snapinsight.compare",
            {
                "route": "/v1/compare/products",
                "operation": "compare_products",
                "compare_used": True,
                "status": "error",
                "status_code": 400,
                "error_type": "compare_invalid_request",
                "fields_count": len(payload),
                "latency_ms": elapsed_ms,
            },
        )
        return build_compare_error_response(
            status_code=400,
            error="compare_invalid_request",
            message="Compare requires two valid analysis results.",
            request_id=request_id,
            latency_ms=elapsed_ms,
        )

    try:
        # Compare is deterministic and uses only supplied analysis data.
        response = compare_products(
            request=request,
            request_id=request_id,
            started_at=start_time,
        )
        trace_backend_event(
            "snapinsight.compare",
            {
                "route": "/v1/compare/products",
                "operation": "compare_products",
                "compare_used": True,
                "status": "ok",
                "status_code": 200,
                "diff_count": len(response.differences),
                "citations_used_count": len(response.citations_used),
                "warnings_count": len(response.warnings),
                "latency_ms": response.latency_ms,
            },
        )
        return response
    except ProductCompareError as exc:
        trace_backend_event(
            "snapinsight.compare",
            {
                "route": "/v1/compare/products",
                "operation": "compare_products",
                "compare_used": True,
                "status": "error",
                "status_code": exc.status_code,
                "error_type": exc.error,
                "latency_ms": exc.latency_ms,
            },
        )
        return build_compare_error_response(
            status_code=exc.status_code,
            error=exc.error,
            message=exc.message,
            request_id=request_id,
            latency_ms=exc.latency_ms,
        )
