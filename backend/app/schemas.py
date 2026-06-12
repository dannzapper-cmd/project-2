from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str
    version: str
    analysis_mode: str
    gemini_configured: bool
    mock_fallback_allowed: bool
    cache_enabled: bool = True
    llmops_enabled: bool = False
    llmops_configured: bool = False
    llmops_provider: str = "disabled"
    llmops_environment: str | None = None
    gemini_live_enabled: bool = False
    gemini_live_configured: bool = False
    gemini_live_provider: str = "gemini_live"
    gemini_live_model: str | None = None


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
    mode: Literal["mock", "gemini", "mock_fallback", "error"]
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
    # Optional cache marker. None = caching disabled / not applicable,
    # False = cache miss (analysis was run), True = served from in-memory cache.
    # Frontend treats None and False the same for display.
    cache_hit: bool | None = None


class MetricsSummaryResponse(BaseModel):
    # Operational counters only. No user data, image data, prompts, chat
    # messages, or product names are exposed here.
    counters: dict[str, int]
    last_latency_ms: int | None = None
    average_latency_ms: int | None = None
    uptime_seconds: int
    llmops_enabled: bool = False
    llmops_configured: bool = False
    llmops_provider: str = "disabled"
    llmops_environment: str | None = None
    gemini_live_enabled: bool = False
    gemini_live_configured: bool = False
    gemini_live_provider: str = "gemini_live"
    gemini_live_model: str | None = None
    usage_limits_storage: str | None = None
    usage_limits_daily_analyses: int | None = None
    usage_limits_daily_estimated_cost_usd: float | None = None
    usage_limits_daily_analysis_limit: int | None = None
    usage_limits_daily_cost_limit_usd: float | None = None
    usage_limits_max_analyses_per_session: int | None = None
    usage_limits_max_chat_messages_per_session: int | None = None
    usage_limits_max_compare_per_session: int | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ProductChatRequest(BaseModel):
    analysis: AnalyzeImageResponse
    messages: list[ChatMessage] = Field(default_factory=list)
    question: str


class ProductChatResponse(BaseModel):
    answer: str
    mode: Literal["gemini", "mock", "mock_fallback", "error"]
    citations_used: list[Citation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    request_id: str
    latency_ms: int = Field(ge=0)


class CompareProductInput(BaseModel):
    label: str
    analysis: AnalyzeImageResponse


class CompareProductsRequest(BaseModel):
    product_a: CompareProductInput
    product_b: CompareProductInput


class CompareFieldDiff(BaseModel):
    field: str
    label: str
    product_a_value: str | None = None
    product_b_value: str | None = None
    status: Literal["same", "different", "missing_a", "missing_b", "missing_both"]
    note: str | None = None


class CompareProductsResponse(BaseModel):
    summary: str
    differences: list[CompareFieldDiff] = Field(default_factory=list)
    citations_used: list[Citation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    request_id: str
    latency_ms: int = Field(ge=0)


GraphNodeType = Literal[
    "product",
    "brand",
    "category",
    "nutrition",
    "ingredient",
    "additive",
    "warning",
    "citation",
    "alternative",
]

GraphBackend = Literal["memory", "neo4j", "neo4j_fallback"]


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    detail: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    field: str | None = None
    url: str | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    label: str | None = None


class EvidencePathStep(BaseModel):
    node_id: str
    node_type: GraphNodeType
    label: str


class EvidencePath(BaseModel):
    id: str
    path_type: Literal[
        "warning_nutrition_citation",
        "additive_warning_citation",
        "alternative_category_citation",
        "insight_citation",
    ]
    summary: str
    steps: list[EvidencePathStep] = Field(default_factory=list)
    citation_field: str | None = None


class ProductGraphRequest(BaseModel):
    analysis: AnalyzeImageResponse


class ProductGraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    evidence_paths: list[EvidencePath] = Field(default_factory=list)
    graph_backend: GraphBackend = "memory"
    graph_enabled: bool = True
    request_id: str
    latency_ms: int = Field(ge=0)


class GeminiLiveConfigResponse(BaseModel):
    enabled: bool
    configured: bool
    provider: str = "gemini_live"
    model: str
    audio_enabled: bool
    vision_enabled: bool
    max_session_seconds: int = Field(ge=1)
    max_frames_per_second: int = Field(ge=1)
    requires_access_code: bool
    status: Literal["disabled", "not_configured", "ready"]


class GeminiLiveTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_code: str | None = Field(default=None, max_length=256)


class GeminiLiveTokenResponse(BaseModel):
    status: Literal[
        "ready",
        "disabled",
        "not_configured",
        "access_denied",
        "rate_limited",
        "token_error",
    ]
    enabled: bool
    configured: bool
    provider: str = "gemini_live"
    model: str
    token: str | None = None
    websocket_url: str | None = None
    expires_in_seconds: int | None = None
    modality: Literal["audio_with_transcription"] = "audio_with_transcription"
    audio_enabled: bool
    vision_enabled: bool
    max_session_seconds: int = Field(ge=1)
    max_frames_per_second: int = Field(ge=1)
    requires_access_code: bool
    message: str | None = None


LiveTelemetryEvent = Literal[
    "live_session_started",
    "live_session_connected",
    "live_session_ended",
    "live_session_error",
]


class GeminiLiveTelemetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: LiveTelemetryEvent
    duration_seconds: float | None = Field(default=None, ge=0, le=3600)
    frames_sent_count: int | None = Field(default=None, ge=0, le=10000)
    audio_enabled: bool | None = None
    vision_enabled: bool | None = None
    text_messages_count: int | None = Field(default=None, ge=0, le=1000)
    model: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=80)
    error_type: str | None = Field(default=None, max_length=120)


class GeminiLiveTelemetryResponse(BaseModel):
    status: Literal["accepted"]
    request_id: str
