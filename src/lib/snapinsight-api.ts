const API_BASE = process.env.NEXT_PUBLIC_SNAPINSIGHT_API_URL

export interface AnalysisConfidence {
  score: number
  label: string
}

export interface AnalysisProduct {
  display_name: string
  category: string
  brand: string | null
  detected_attributes: string[]
  confidence: AnalysisConfidence
  barcode: string | null
}

export type GroundingStatus =
  | "grounded"
  | "partial_match"
  | "no_match"
  | "grounding_unavailable"

export type MatchMethod = "barcode" | "name_brand" | "name_only" | "none"

export interface NutritionSummary {
  energy_kcal_100g: string | null
  sugars_100g: string | null
  fat_100g: string | null
  saturated_fat_100g: string | null
  proteins_100g: string | null
  salt_100g: string | null
}

export interface ProductEnrichment {
  nutrition_summary: NutritionSummary | null
  nutrition_grade: string | null
  labels: string[]
  additives: string[]
  enrichment_source_confidence: string | null
  enrichment_notes: string[]
}

export interface AnalysisInsight {
  title: string
  body: string
  type: string
}

export interface AnalysisCitation {
  source: string
  title: string
  field: string
  field_label: string
  value: string
  url: string | null
}

export interface AnalysisPrivacy {
  image_stored: boolean
  image_retention: string
}

export interface AnalysisMeta {
  model: string
  latency_ms: number
  api_version: string
}

export interface AnalysisResponse {
  request_id: string
  mode: "mock" | "gemini" | "mock_fallback"
  status: "completed"
  product: AnalysisProduct
  insights: AnalysisInsight[]
  warnings: string[]
  citations: AnalysisCitation[]
  next_questions: string[]
  privacy: AnalysisPrivacy
  meta: AnalysisMeta
  grounding_status: GroundingStatus
  grounding_summary: string
  match_method: MatchMethod | null
  source_product_id: string | null
  retrieved_at: string | null
  source_trace: string[]
  product_enrichment: ProductEnrichment | null
  // null = caching disabled / not applicable, false = cache miss,
  // true = served from the backend in-memory cache. Treat null and false alike.
  cache_hit?: boolean | null
}

export interface HealthResponse {
  status: string
  service: string
  mode: string
  version: string
  analysis_mode: string
  gemini_configured: boolean
  mock_fallback_allowed: boolean
  cache_enabled: boolean
  llmops_enabled?: boolean
  llmops_configured?: boolean
  llmops_provider?: "langfuse" | "disabled"
  llmops_environment?: string | null
}

export interface MetricsSummaryResponse {
  counters: Record<string, number>
  last_latency_ms: number | null
  average_latency_ms: number | null
  uptime_seconds: number
  llmops_enabled?: boolean
  llmops_configured?: boolean
  llmops_provider?: "langfuse" | "disabled"
  llmops_environment?: string | null
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

export interface ProductChatResponse {
  answer: string
  mode: "gemini" | "mock" | "mock_fallback" | "error"
  citations_used: AnalysisCitation[]
  warnings: string[]
  request_id: string
  latency_ms: number
}

export type CompareStatus =
  | "same"
  | "different"
  | "missing_a"
  | "missing_b"
  | "missing_both"

export interface CompareFieldDiff {
  field: string
  label: string
  product_a_value: string | null
  product_b_value: string | null
  status: CompareStatus
  note: string | null
}

export interface CompareProductsResponse {
  summary: string
  differences: CompareFieldDiff[]
  citations_used: AnalysisCitation[]
  warnings: string[]
  request_id: string
  latency_ms: number
}

export type GraphNodeType =
  | "product"
  | "brand"
  | "category"
  | "nutrition"
  | "ingredient"
  | "additive"
  | "warning"
  | "citation"
  | "alternative"

export type GraphBackend = "memory" | "neo4j" | "neo4j_fallback"

export interface GraphNode {
  id: string
  type: GraphNodeType
  label: string
  detail: string | null
  confidence: number | null
  field: string | null
  url: string | null
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationship: string
  label: string | null
}

export interface EvidencePathStep {
  node_id: string
  node_type: GraphNodeType
  label: string
}

export interface EvidencePath {
  id: string
  path_type:
    | "warning_nutrition_citation"
    | "additive_warning_citation"
    | "alternative_category_citation"
    | "insight_citation"
  summary: string
  steps: EvidencePathStep[]
  citation_field: string | null
}

export interface ProductGraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  evidence_paths: EvidencePath[]
  graph_backend: GraphBackend
  graph_enabled: boolean
  request_id: string
  latency_ms: number
}

interface ApiErrorBody {
  detail?: string
  error?: string
  mode?: "error"
  message?: string
  request_id?: string
  latency_ms?: number
}

export function getApiBase(): string {
  if (API_BASE) return API_BASE

  if (process.env.NODE_ENV === "development") {
    return "http://127.0.0.1:8000"
  }

  throw new Error(
    "NEXT_PUBLIC_SNAPINSIGHT_API_URL is not configured. " +
      "Set it in your environment before building."
  )
}

async function getErrorDetail(
  response: Response,
  fallback: string
): Promise<string> {
  let detail = fallback

  try {
    const errorBody = (await response.json()) as ApiErrorBody
    if (errorBody.message) {
      detail = errorBody.message
    } else if (errorBody.detail) {
      detail = errorBody.detail
    }
  } catch {
    // Keep the generic status message when the backend returns non-JSON.
  }

  return detail
}

export async function analyzeImage(
  file: File,
  signal?: AbortSignal
): Promise<AnalysisResponse> {
  const formData = new FormData()
  formData.append("file", file, file.name)

  const response = await fetch(`${getApiBase()}/v1/analyze/image`, {
    method: "POST",
    body: formData,
    signal,
  })

  if (!response.ok) {
    throw new Error(
      await getErrorDetail(
        response,
        `Analysis request failed with status ${response.status}.`
      )
    )
  }

  return response.json() as Promise<AnalysisResponse>
}

export async function chatWithProduct(
  analysis: AnalysisResponse,
  messages: ChatMessage[],
  question: string,
  signal?: AbortSignal
): Promise<ProductChatResponse> {
  const response = await fetch(`${getApiBase()}/v1/chat/product`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ analysis, messages, question }),
    signal,
  })

  if (!response.ok) {
    throw new Error(
      await getErrorDetail(
        response,
        `Chat request failed with status ${response.status}.`
      )
    )
  }

  return response.json() as Promise<ProductChatResponse>
}

export async function compareProducts(
  productA: AnalysisResponse,
  productB: AnalysisResponse,
  signal?: AbortSignal
): Promise<CompareProductsResponse> {
  const response = await fetch(`${getApiBase()}/v1/compare/products`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    // Compare sends existing analysis JSON only; no image or audio bytes.
    body: JSON.stringify({
      product_a: { label: "A", analysis: productA },
      product_b: { label: "B", analysis: productB },
    }),
    signal,
  })

  if (!response.ok) {
    throw new Error(
      await getErrorDetail(
        response,
        `Compare request failed with status ${response.status}.`
      )
    )
  }

  return response.json() as Promise<CompareProductsResponse>
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${getApiBase()}/health`, { signal })
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}.`)
  }
  return response.json() as Promise<HealthResponse>
}

export async function getMetricsSummary(
  signal?: AbortSignal
): Promise<MetricsSummaryResponse> {
  const response = await fetch(`${getApiBase()}/v1/metrics/summary`, { signal })
  if (!response.ok) {
    throw new Error(`Metrics request failed with status ${response.status}.`)
  }
  return response.json() as Promise<MetricsSummaryResponse>
}

export async function fetchProductGraph(
  analysis: AnalysisResponse,
  signal?: AbortSignal
): Promise<ProductGraphResponse> {
  const response = await fetch(`${getApiBase()}/v1/graph/product`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ analysis }),
    signal,
  })

  if (!response.ok) {
    throw new Error(
      await getErrorDetail(
        response,
        `Graph request failed with status ${response.status}.`
      )
    )
  }

  return response.json() as Promise<ProductGraphResponse>
}
