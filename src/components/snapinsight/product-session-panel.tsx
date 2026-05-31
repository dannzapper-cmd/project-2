"use client"

import {
  ArrowDown,
  ArrowUp,
  Layers,
  Minus,
  Play,
  Square,
} from "lucide-react"

import type { AnalysisResponse } from "@/lib/snapinsight-api"
import {
  getSessionSummary,
  MAX_SESSION_SNAPSHOTS,
  type ConfidenceTrendDirection,
  type ProductSession,
} from "@/lib/product-session"

function formatSnapshotTime(ms: number): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(ms))
}

function formatConfidence(analysis: AnalysisResponse): string {
  const { label, score } = analysis.product.confidence
  return `${label} · ${Math.round(score * 100)}%`
}

function getModeLabel(mode: AnalysisResponse["mode"]): string {
  if (mode === "gemini") return "AI"
  if (mode === "mock_fallback") return "Fallback"
  return "Mock"
}

function getGroundingLabel(status: AnalysisResponse["grounding_status"]): string {
  if (status === "grounded") return "Grounded"
  if (status === "partial_match") return "Partial"
  if (status === "grounding_unavailable") return "Unavailable"
  return "No match"
}

function TrendIcon({ trend }: { trend: ConfidenceTrendDirection }) {
  if (trend === "up") {
    return <ArrowUp className="h-3.5 w-3.5 text-emerald-400" aria-label="Higher confidence" />
  }
  if (trend === "down") {
    return <ArrowDown className="h-3.5 w-3.5 text-red-400" aria-label="Lower confidence" />
  }
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" aria-label="Same or first snapshot" />
}

interface ProductSessionPanelProps {
  sessionModeEnabled: boolean
  onSessionModeChange: (enabled: boolean) => void
  session: ProductSession | null
  onStartSession: () => void
  onEndSession: () => void
  sessionLimitReached: boolean
}

export function ProductSessionPanel({
  sessionModeEnabled,
  onSessionModeChange,
  session,
  onStartSession,
  onEndSession,
  sessionLimitReached,
}: ProductSessionPanelProps) {
  const summary = getSessionSummary(session)
  const atLimit = (session?.snapshots.length ?? 0) >= MAX_SESSION_SNAPSHOTS

  return (
    <section className="glass-card mt-4 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-violet-300" />
          <div>
            <h3 className="text-sm font-semibold text-foreground">Session Mode</h3>
            <p className="text-xs text-muted-foreground">
              Multi-scan timeline for the same product — not video streaming.
            </p>
          </div>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
          <span>Enable</span>
          <input
            type="checkbox"
            checked={sessionModeEnabled}
            onChange={(event) => onSessionModeChange(event.target.checked)}
            className="h-4 w-4 rounded border-white/20 bg-slate-800 accent-violet-500"
          />
        </label>
      </div>

      {sessionModeEnabled && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {!session ? (
              <button
                type="button"
                onClick={onStartSession}
                className="inline-flex touch-target items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/15 px-4 py-2 text-sm font-medium text-violet-200 hover:bg-violet-500/25"
              >
                <Play className="h-4 w-4" />
                Start session
              </button>
            ) : (
              <button
                type="button"
                onClick={onEndSession}
                className="inline-flex touch-target items-center gap-2 rounded-full border border-white/10 bg-slate-800/80 px-4 py-2 text-sm font-medium text-foreground hover:bg-slate-700/80"
              >
                <Square className="h-4 w-4" />
                End session
              </button>
            )}
          </div>

          {sessionLimitReached && (
            <p className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              Session limit reached. Start a new session.
            </p>
          )}

          {session && summary.snapshotCount > 0 && (
            <div className="rounded-2xl border border-white/5 bg-slate-800/40 p-3">
              <p className="mono-label mb-2 text-muted-foreground">Session summary</p>
              <div className="grid gap-2 text-sm sm:grid-cols-2">
                <p className="text-muted-foreground">
                  Snapshots:{" "}
                  <span className="font-medium text-foreground">
                    {summary.snapshotCount}
                    {atLimit ? ` / ${MAX_SESSION_SNAPSHOTS}` : ""}
                  </span>
                </p>
                <p className="text-muted-foreground">
                  Best match:{" "}
                  <span className="font-medium text-foreground">
                    {summary.bestProductName ?? "—"}
                  </span>
                </p>
                <p className="text-muted-foreground sm:col-span-2">
                  Grounding seen:{" "}
                  <span className="font-medium text-foreground">
                    {summary.groundingStatusesSeen.length > 0
                      ? summary.groundingStatusesSeen
                          .map((status) => getGroundingLabel(status))
                          .join(", ")
                      : "—"}
                  </span>
                </p>
                <p className="text-muted-foreground">
                  Latest citations:{" "}
                  <span className="font-medium text-foreground">
                    {summary.latestCitationCount}
                  </span>
                </p>
                <p className="text-muted-foreground">
                  Latest mode:{" "}
                  <span className="font-medium text-foreground">
                    {summary.latestMode ? getModeLabel(summary.latestMode) : "—"}
                  </span>
                </p>
              </div>
              {summary.latestWarnings.length > 0 && (
                <p className="mt-2 text-xs text-amber-200/90">
                  Latest warnings: {summary.latestWarnings.join(" · ")}
                </p>
              )}
            </div>
          )}

          {session && session.snapshots.length > 0 && (
            <div>
              <p className="mono-label mb-2 text-muted-foreground">Snapshot timeline</p>
              <ol className="space-y-2">
                {session.snapshots.map((snapshot, index) => {
                  const trend = summary.confidenceTrends[index] ?? "neutral"
                  const analysis = snapshot.analysis
                  return (
                    <li
                      key={snapshot.localKey}
                      className="rounded-2xl border border-white/5 bg-slate-900/50 px-3 py-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-violet-200">
                            Snapshot #{snapshot.order}
                            <span className="ml-2 font-normal text-muted-foreground">
                              {formatSnapshotTime(snapshot.capturedAtMs)}
                            </span>
                          </p>
                          <p className="mt-1 truncate text-sm font-medium text-foreground">
                            {analysis.product.display_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {analysis.product.category}
                          </p>
                        </div>
                        <TrendIcon trend={trend} />
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2 py-0.5 text-muted-foreground">
                          {formatConfidence(analysis)}
                        </span>
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2 py-0.5 text-muted-foreground">
                          {getGroundingLabel(analysis.grounding_status)}
                        </span>
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2 py-0.5 text-muted-foreground">
                          {analysis.warnings.length} warning
                          {analysis.warnings.length === 1 ? "" : "s"}
                        </span>
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2 py-0.5 text-muted-foreground">
                          {getModeLabel(analysis.mode)}
                          {analysis.cache_hit === true ? " · cached" : ""}
                        </span>
                      </div>
                      {index === session.snapshots.length - 1 && (
                        <p className="mt-2 text-[11px] text-violet-300/90">
                          Active for result card, chat, compare, and graph.
                        </p>
                      )}
                    </li>
                  )
                })}
              </ol>
            </div>
          )}

          {session && session.snapshots.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Session started. Analyze an image to add snapshot #1.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
