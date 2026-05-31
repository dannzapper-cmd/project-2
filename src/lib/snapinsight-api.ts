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
