from app.schemas import (
    AnalyzeImageResponse,
    Confidence,
    Insight,
    PrivacySummary,
    ProductSummary,
    ResponseMeta,
)


def build_mock_image_analysis_response(
    *, request_id: str, latency_ms: int, api_version: str
) -> AnalyzeImageResponse:
    """Build a stable mock contract response without calling an AI model."""
    return AnalyzeImageResponse(
        request_id=request_id,
        mode="mock",
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
        warnings=[
            "Mock/demo response only; no AI model was called.",
            "No image was stored.",
        ],
        citations=[],
        next_questions=[
            "What product is this?",
            "What would you like to know about it?",
        ],
        privacy=PrivacySummary(image_stored=False, image_retention="none"),
        meta=ResponseMeta(
            model="none",
            latency_ms=latency_ms,
            api_version=api_version,
        ),
    )
