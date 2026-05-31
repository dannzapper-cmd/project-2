import logging
import os
import time
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import ConfigurationError, get_effective_analysis_mode, get_settings
from app.schemas import AnalyzeImageResponse, HealthResponse
from app.services.analysis_router import (
    AnalysisUnavailableError,
    analyze_product_image,
)


SERVICE_NAME = "snapinsight-backend"
APP_VERSION = "0.1.0"
API_VERSION = "v1"
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_FILE_SIZE_MB = MAX_FILE_SIZE_BYTES // (1024 * 1024)
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
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


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    try:
        settings = get_settings()
    except ConfigurationError as exc:
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
    )


@app.post("/v1/analyze/image", response_model=AnalyzeImageResponse)
async def analyze_image(
    file: UploadFile = File(...),
) -> AnalyzeImageResponse | JSONResponse:
    start_time = time.monotonic()
    request_id = str(uuid.uuid4())

    try:
        settings = get_settings()
    except ConfigurationError as exc:
        return build_error_response(
            status_code=500,
            error="invalid_analysis_mode",
            message=exc.message,
            request_id=request_id,
            latency_ms=int((time.monotonic() - start_time) * 1000),
        )

    content_type = file.content_type or ""

    # This MIME type is client-declared and not verified against file magic
    # bytes yet. Magic byte validation is a future hardening step.
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload an image/* file.",
        )

    try:
        contents = await file.read()
    finally:
        await file.close()

    file_size_bytes = len(contents)
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum supported size is {MAX_FILE_SIZE_MB}MB.",
        )

    # Privacy: image bytes are not logged or persisted.
    logger.info(
        "Image analysis request accepted",
        extra={
            "request_id": request_id,
            "content_type": content_type,
            "file_size_bytes": file_size_bytes,
        },
    )

    try:
        return await analyze_product_image(
            request_id=request_id,
            image_bytes=contents,
            content_type=content_type,
            started_at=start_time,
            api_version=API_VERSION,
            settings=settings,
        )
    except AnalysisUnavailableError as exc:
        return build_error_response(
            status_code=exc.status_code,
            error=exc.error,
            message=exc.message,
            request_id=request_id,
            latency_ms=exc.latency_ms,
        )
