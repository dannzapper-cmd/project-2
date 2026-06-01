export const ANALYSIS_SERVICE_UNREACHABLE_MESSAGE =
  "Analysis service is unreachable. The backend may be waking up, the API URL may be missing, or this Vercel preview may not be allowed by CORS. Try again in a moment or check deployment settings."

export const LIVE_CONFIG_UNREACHABLE_MESSAGE =
  "Could not reach the backend to load Live configuration. This is usually an API URL, CORS, or Render cold-start issue - not a Gemini Live failure."

function isApiBaseConfigurationError(error: Error): boolean {
  return error.message.includes("NEXT_PUBLIC_SNAPINSIGHT_API_URL")
}

export function isDeploymentFetchError(err: unknown): boolean {
  return (
    err instanceof TypeError ||
    (err instanceof Error && isApiBaseConfigurationError(err))
  )
}

export function getAnalysisServiceErrorMessage(err: unknown): string {
  if (isDeploymentFetchError(err)) {
    return ANALYSIS_SERVICE_UNREACHABLE_MESSAGE
  }

  if (err instanceof Error) {
    return err.message
  }

  return ANALYSIS_SERVICE_UNREACHABLE_MESSAGE
}
