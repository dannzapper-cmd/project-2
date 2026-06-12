const CLIENT_SESSION_STORAGE_KEY = "snapinsight-client-session-id"

function createClientSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }

  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function getClientSessionId(): string {
  if (typeof window === "undefined") {
    return "server-render"
  }

  const existing = window.sessionStorage.getItem(CLIENT_SESSION_STORAGE_KEY)
  if (existing) {
    return existing
  }

  const created = createClientSessionId()
  window.sessionStorage.setItem(CLIENT_SESSION_STORAGE_KEY, created)
  return created
}

export const CLIENT_SESSION_HEADER = "X-SnapInsight-Session-Id"
