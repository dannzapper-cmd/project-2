from typing import Literal

from app.schemas import (
    AnalyzeImageResponse,
    Confidence,
    Insight,
    PrivacySummary,
    ProductSummary,
    ResponseMeta,
)


MockMode = Literal["mock", "mock_fallback"]


def build_mock_image_analysis_response(
    *,
    request_id: str,
    latency_ms: int,
    api_version: str,
    mode: MockMode = "mock",
    warnings: list[str] | None = None,
    model: str = "none",
) -> AnalyzeImageResponse:
    """Build a stable mock contract response without calling an AI model."""
    response_warnings = warnings or [
        "Mock/demo response only; no AI model was called.",
        "No image was stored.",
    ]

    return AnalyzeImageResponse(
        request_id=request_id,
        mode=mode,
        status="completed",
        product=ProductSummary(
            display_name="Product image received",
            category="unknown",
            brand=None,
            detected_attributes=[
                "Image accepted",
                "Ready for future multimodal analysis",
            ],
            confidence=Confidence(score=0.0, label="mock"),
            barcode=None,
        ),
        insights=[
            Insight(
                title="Analysis not connected yet",
                body=(
                    "This response is a mock contract for the future "
                    "multimodal pipeline."
                ),
                type="system",
            )
        ],
        warnings=response_warnings,
        citations=[],
        next_questions=[
            "What product is this?",
            "What would you like to know about it?",
        ],
        privacy=PrivacySummary(image_stored=False, image_retention="none"),
        meta=ResponseMeta(
            model=model,
            latency_ms=latency_ms,
            api_version=api_version,
        ),
    )
