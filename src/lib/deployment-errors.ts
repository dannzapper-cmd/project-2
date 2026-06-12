export const ANALYSIS_SERVICE_UNREACHABLE_MESSAGE =
  "Analysis service is unreachable. The backend may be waking up, the API URL may be missing, or this Vercel preview may not be allowed by CORS. Try again in a moment or check deployment settings."

export const LIVE_CONFIG_UNREACHABLE_MESSAGE =
  "Could not reach the backend to load Live configuration. This is usually an API URL, CORS, or Render cold-start issue - not a Gemini Live failure."

export const PUBLIC_DEMO_LIMIT_PREFIX =
  "This public demo has usage limits to control AI costs."

const USAGE_LIMIT_ERROR_CODES = new Set([
  "session_analysis_limit",
  "session_chat_limit",
  "session_compare_limit",
  "daily_analysis_limit",
  "daily_cost_limit",
])

const USAGE_LIMIT_MESSAGE_HINTS = [
  "analysis limit for this session",
  "chat message limit for this session",
  "compare limit for this session",
  "daily analysis limit",
  "daily estimated gemini cost limit",
  "reached the analysis limit",
  "reached the chat message limit",
  "reached the compare limit",
]

function isApiBaseConfigurationError(error: Error): boolean {
  return error.message.includes("NEXT_PUBLIC_SNAPINSIGHT_API_URL")
}

export function isDeploymentFetchError(err: unknown): boolean {
  return (
    err instanceof TypeError ||
    (err instanceof Error && isApiBaseConfigurationError(err))
  )
}

export function isUsageLimitErrorMessage(message: string): boolean {
  const normalized = message.toLowerCase()
  return USAGE_LIMIT_MESSAGE_HINTS.some((hint) => normalized.includes(hint))
}

export function isUsageLimitApiError(errorCode: string | undefined): boolean {
  return Boolean(errorCode && USAGE_LIMIT_ERROR_CODES.has(errorCode))
}

export function getSnapInsightApiErrorMessage(err: unknown): string {
  if (isDeploymentFetchError(err)) {
    return ANALYSIS_SERVICE_UNREACHABLE_MESSAGE
  }

  if (err instanceof Error) {
    if (
      isUsageLimitErrorMessage(err.message) &&
      !err.message.toLowerCase().includes("public demo")
    ) {
      return `${PUBLIC_DEMO_LIMIT_PREFIX} ${err.message}`
    }
    return err.message
  }

  return ANALYSIS_SERVICE_UNREACHABLE_MESSAGE
}

export function getAnalysisServiceErrorMessage(err: unknown): string {
  return getSnapInsightApiErrorMessage(err)
}
