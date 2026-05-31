import type { AnalysisResponse, GroundingStatus } from "@/lib/snapinsight-api"

export const MAX_SESSION_SNAPSHOTS = 10

export type ConfidenceTrendDirection = "up" | "down" | "neutral"

export interface SessionSnapshot {
  /** Ephemeral React list key only; not persisted or sent to backend. */
  localKey: string
  order: number
  capturedAtMs: number
  analysis: AnalysisResponse
}

export interface ProductSession {
  startedAtMs: number
  snapshots: SessionSnapshot[]
}

export interface SessionSummary {
  snapshotCount: number
  bestProductName: string | null
  bestConfidenceScore: number | null
  confidenceTrends: ConfidenceTrendDirection[]
  groundingStatusesSeen: GroundingStatus[]
  latestWarnings: string[]
  latestCitationCount: number
  latestMode: AnalysisResponse["mode"] | null
}

export type AddSnapshotResult =
  | { session: ProductSession; added: true }
  | { session: ProductSession; added: false; reason: "limit_reached" }

export function createProductSession(nowMs: number = Date.now()): ProductSession {
  return {
    startedAtMs: nowMs,
    snapshots: [],
  }
}

export function getConfidenceTrend(
  currentScore: number,
  previousScore: number | null
): ConfidenceTrendDirection {
  if (previousScore === null) return "neutral"
  if (currentScore > previousScore) return "up"
  if (currentScore < previousScore) return "down"
  return "neutral"
}

export function addSnapshotToSession(
  session: ProductSession,
  analysis: AnalysisResponse,
  options?: { nowMs?: number; localKey?: string }
): AddSnapshotResult {
  if (session.snapshots.length >= MAX_SESSION_SNAPSHOTS) {
    return { session, added: false, reason: "limit_reached" }
  }

  const snapshot: SessionSnapshot = {
    localKey: options?.localKey ?? `snap-${session.snapshots.length + 1}`,
    order: session.snapshots.length + 1,
    capturedAtMs: options?.nowMs ?? Date.now(),
    analysis,
  }

  return {
    session: {
      ...session,
      snapshots: [...session.snapshots, snapshot],
    },
    added: true,
  }
}

export function getLatestSessionAnalysis(
  session: ProductSession | null
): AnalysisResponse | null {
  if (!session || session.snapshots.length === 0) return null
  return session.snapshots[session.snapshots.length - 1].analysis
}

export function getSessionSummary(session: ProductSession | null): SessionSummary {
  const empty: SessionSummary = {
    snapshotCount: 0,
    bestProductName: null,
    bestConfidenceScore: null,
    confidenceTrends: [],
    groundingStatusesSeen: [],
    latestWarnings: [],
    latestCitationCount: 0,
    latestMode: null,
  }

  if (!session || session.snapshots.length === 0) {
    return empty
  }

  let bestProductName: string | null = null
  let bestConfidenceScore: number | null = null
  const confidenceTrends: ConfidenceTrendDirection[] = []
  const groundingSeen = new Set<GroundingStatus>()
  const groundingStatusesSeen: GroundingStatus[] = []

  for (const snapshot of session.snapshots) {
    const score = snapshot.analysis.product.confidence.score
    const previousScore =
      snapshot.order === 1
        ? null
        : session.snapshots[snapshot.order - 2].analysis.product.confidence.score

    confidenceTrends.push(getConfidenceTrend(score, previousScore))

    if (bestConfidenceScore === null || score > bestConfidenceScore) {
      bestConfidenceScore = score
      bestProductName = snapshot.analysis.product.display_name
    }

    const status = snapshot.analysis.grounding_status
    if (!groundingSeen.has(status)) {
      groundingSeen.add(status)
      groundingStatusesSeen.push(status)
    }
  }

  const latest = session.snapshots[session.snapshots.length - 1].analysis

  return {
    snapshotCount: session.snapshots.length,
    bestProductName,
    bestConfidenceScore,
    confidenceTrends,
    groundingStatusesSeen,
    latestWarnings: latest.warnings.slice(0, 5),
    latestCitationCount: latest.citations.length,
    latestMode: latest.mode,
  }
}
