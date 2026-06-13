import type { AnalysisResponse, GroundingStatus } from "@/lib/snapinsight-api"

const LATEST_ANALYSIS_KEY = "snapinsight-latest-analysis"
const ANALYSIS_HISTORY_KEY = "snapinsight-analysis-history"
const ACTIVITY_LOG_KEY = "snapinsight-activity-log"
const MAX_HISTORY = 10

export interface AnalysisActivityEntry {
  id: string
  timestamp: string
  product_name: string
  model: string
  latency_ms: number
  confidence_score: number
  confidence_label: string
  cache_hit: boolean | null
  grounding_status: GroundingStatus
  request_id: string
}

export interface StoredAnalysisRecord {
  stored_at: string
  analysis: AnalysisResponse
}

export interface AnalysisStorageSnapshot {
  latest: AnalysisResponse | null
  storedAt: string | null
  history: StoredAnalysisRecord[]
  activity: AnalysisActivityEntry[]
}

function isBrowser(): boolean {
  return typeof window !== "undefined"
}

export function buildActivityEntry(analysis: AnalysisResponse): AnalysisActivityEntry {
  return {
    id: analysis.request_id,
    timestamp: new Date().toISOString(),
    product_name: analysis.product.display_name,
    model: analysis.meta.model,
    latency_ms: analysis.meta.latency_ms,
    confidence_score: analysis.product.confidence.score,
    confidence_label: analysis.product.confidence.label,
    cache_hit: analysis.cache_hit ?? null,
    grounding_status: analysis.grounding_status,
    request_id: analysis.request_id,
  }
}

function notifyStorageChange(): void {
  if (!isBrowser()) return
  window.dispatchEvent(new Event("snapinsight-storage-change"))
}

/** Persist analysis JSON only — no images, base64, or secrets. */
export function persistSuccessfulAnalysis(analysis: AnalysisResponse): void {
  if (!isBrowser()) return

  const record: StoredAnalysisRecord = {
    stored_at: new Date().toISOString(),
    analysis,
  }

  try {
    localStorage.setItem(LATEST_ANALYSIS_KEY, JSON.stringify(record))
  } catch {
    // Quota or private browsing — fail silently.
  }

  try {
    const history = readAnalysisHistory()
    const filtered = history.filter(
      (item) => item.analysis.request_id !== analysis.request_id
    )
    const updated = [record, ...filtered].slice(0, MAX_HISTORY)
    localStorage.setItem(ANALYSIS_HISTORY_KEY, JSON.stringify(updated))
  } catch {
    // ignore
  }

  appendActivityEntry(buildActivityEntry(analysis))
  notifyStorageChange()
}

export function appendActivityEntry(entry: AnalysisActivityEntry): void {
  if (!isBrowser()) return
  try {
    const existing = getActivityLog()
    const filtered = existing.filter((item) => item.request_id !== entry.request_id)
    const updated = [entry, ...filtered].slice(0, MAX_HISTORY)
    sessionStorage.setItem(ACTIVITY_LOG_KEY, JSON.stringify(updated))
  } catch {
    // ignore
  }
}

export function getActivityLog(): AnalysisActivityEntry[] {
  if (!isBrowser()) return []
  try {
    const raw = sessionStorage.getItem(ACTIVITY_LOG_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as AnalysisActivityEntry[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function getLatestAnalysis(): AnalysisResponse | null {
  if (!isBrowser()) return null
  try {
    const raw = localStorage.getItem(LATEST_ANALYSIS_KEY)
    if (!raw) return null
    const record = JSON.parse(raw) as StoredAnalysisRecord
    return record.analysis ?? null
  } catch {
    return null
  }
}

export function getLatestAnalysisStoredAt(): string | null {
  if (!isBrowser()) return null
  try {
    const raw = localStorage.getItem(LATEST_ANALYSIS_KEY)
    if (!raw) return null
    const record = JSON.parse(raw) as StoredAnalysisRecord
    return record.stored_at ?? null
  } catch {
    return null
  }
}

function readAnalysisHistory(): StoredAnalysisRecord[] {
  if (!isBrowser()) return []
  try {
    const raw = localStorage.getItem(ANALYSIS_HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as StoredAnalysisRecord[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function getAnalysisHistory(): StoredAnalysisRecord[] {
  return readAnalysisHistory()
}
