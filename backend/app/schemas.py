from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str
    version: str
    analysis_mode: str
    gemini_configured: bool
    mock_fallback_allowed: bool


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    label: str


class ProductSummary(BaseModel):
    display_name: str
    category: str
    brand: str | None
    detected_attributes: list[str]
    confidence: Confidence
    barcode: str | None = None


class Insight(BaseModel):
    title: str
    body: str
    type: str


class Citation(BaseModel):
    source: str = "OpenFoodFacts"
    title: str
    field: str
    field_label: str
    value: str
    url: str | None = None


class NutritionSummary(BaseModel):
    # All values are display-ready strings, not floats for calculation.
    energy_kcal_100g: str | None = None
    sugars_100g: str | None = None
    fat_100g: str | None = None
    saturated_fat_100g: str | None = None
    proteins_100g: str | None = None
    salt_100g: str | None = None

    @property
    def has_any(self) -> bool:
        return any(
            [
                self.energy_kcal_100g,
                self.sugars_100g,
                self.fat_100g,
                self.saturated_fat_100g,
                self.proteins_100g,
                self.salt_100g,
            ]
        )


class ProductEnrichment(BaseModel):
    nutrition_summary: NutritionSummary | None = None
    nutrition_grade: str | None = None
    labels: list[str] = Field(default_factory=list)
    additives: list[str] = Field(default_factory=list)
    enrichment_source_confidence: str | None = None
    enrichment_notes: list[str] = Field(default_factory=list)


class GroundingResult(BaseModel):
    grounding_status: Literal[
        "grounded",
        "partial_match",
        "no_match",
        "grounding_unavailable",
    ]
    grounding_summary: str
    match_method: Literal["barcode", "name_brand", "name_only", "none"] | None = None
    source_product_id: str | None = None
    retrieved_at: datetime | None = None
    citations: list[Citation] = Field(default_factory=list)
    source_trace: list[str] = Field(default_factory=list)
    product_enrichment: ProductEnrichment | None = None


class PrivacySummary(BaseModel):
    image_stored: bool
    image_retention: str


class ResponseMeta(BaseModel):
    model: str
    latency_ms: int = Field(ge=0)
    api_version: str


class AnalyzeImageResponse(BaseModel):
    request_id: str
    mode: Literal["mock", "gemini", "mock_fallback"]
    status: Literal["completed"]
    product: ProductSummary
    insights: list[Insight]
    warnings: list[str]
    citations: list[Citation]
    next_questions: list[str]
    privacy: PrivacySummary
    meta: ResponseMeta
    grounding_status: Literal[
        "grounded",
        "partial_match",
        "no_match",
        "grounding_unavailable",
    ] = "no_match"
    grounding_summary: str = "No reliable OpenFoodFacts match found"
    match_method: Literal["barcode", "name_brand", "name_only", "none"] | None = "none"
    source_product_id: str | None = None
    retrieved_at: datetime | None = None
    source_trace: list[str] = Field(default_factory=list)
    product_enrichment: ProductEnrichment | None = None
