from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str
    version: str


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    label: str


class ProductSummary(BaseModel):
    display_name: str
    category: str
    brand: str | None
    detected_attributes: list[str]
    confidence: Confidence


class Insight(BaseModel):
    title: str
    body: str
    type: str


class Citation(BaseModel):
    title: str
    source: str | None = None
    url: str | None = None


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
