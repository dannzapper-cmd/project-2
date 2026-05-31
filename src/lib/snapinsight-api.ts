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
}

export interface AnalysisInsight {
  title: string
  body: string
  type: string
}

export interface AnalysisCitation {
  title: string
  source: string | null
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
    let detail = `Analysis request failed with status ${response.status}.`

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

    throw new Error(detail)
  }

  return response.json() as Promise<AnalysisResponse>
}
