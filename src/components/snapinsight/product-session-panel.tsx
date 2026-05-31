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
    return (
      <ArrowUp
        className="h-3.5 w-3.5 shrink-0 text-emerald-400"
        aria-hidden
      />
    )
  }
  if (trend === "down") {
    return (
      <ArrowDown
        className="h-3.5 w-3.5 shrink-0 text-red-400"
        aria-hidden
      />
    )
  }
  return (
    <Minus
      className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
      aria-hidden
    />
  )
}

function getTrendAriaLabel(trend: ConfidenceTrendDirection): string {
  if (trend === "up") return "Higher than previous snapshot"
  if (trend === "down") return "Lower than previous snapshot"
  return "First snapshot or unchanged"
}

function SessionStatusBadge({
  sessionModeEnabled,
  session,
}: {
  sessionModeEnabled: boolean
  session: ProductSession | null
}) {
  if (!sessionModeEnabled) {
    return (
      <span className="rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
        Off
      </span>
    )
  }
  if (!session) {
    return (
      <span className="rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
        Ready
      </span>
    )
  }
  return (
    <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-200">
      Active · {session.snapshots.length}/{MAX_SESSION_SNAPSHOTS}
    </span>
  )
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
    <section className="glass-card mt-4 p-4 sm:p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <Layers className="mt-0.5 h-4 w-4 shrink-0 text-violet-300" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground">Session Mode</h3>
              <SessionStatusBadge
                sessionModeEnabled={sessionModeEnabled}
                session={session}
              />
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Compare multiple still-image scans of one product in this browser tab
              only. Not live video, screen sharing, or saved history.
            </p>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={sessionModeEnabled}
          onClick={() => onSessionModeChange(!sessionModeEnabled)}
          className="touch-target inline-flex shrink-0 items-center justify-between gap-3 self-start rounded-full border border-white/10 bg-slate-800/80 px-4 py-2.5 text-sm font-medium text-foreground hover:bg-slate-700/80 sm:min-w-[132px]"
        >
          <span className="text-xs text-muted-foreground">Session Mode</span>
          <span
            className={
              sessionModeEnabled
                ? "rounded-full bg-violet-500/25 px-2 py-0.5 text-xs text-violet-200"
                : "rounded-full bg-slate-700/80 px-2 py-0.5 text-xs text-muted-foreground"
            }
          >
            {sessionModeEnabled ? "On" : "Off"}
          </span>
        </button>
      </div>

      {sessionModeEnabled && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            {!session ? (
              <button
                type="button"
                onClick={onStartSession}
                className="touch-target inline-flex w-full items-center justify-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/15 px-4 py-3 text-sm font-medium text-violet-200 hover:bg-violet-500/25 sm:w-auto"
              >
                <Play className="h-4 w-4" />
                Start session
              </button>
            ) : (
              <button
                type="button"
                onClick={onEndSession}
                className="touch-target inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/10 bg-slate-800/80 px-4 py-3 text-sm font-medium text-foreground hover:bg-slate-700/80 sm:w-auto"
              >
                <Square className="h-4 w-4" />
                End session
              </button>
            )}
            {session && (
              <p className="self-center text-xs leading-relaxed text-muted-foreground sm:max-w-[280px]">
                {session.snapshots.length === 0
                  ? "Capture or upload, then tap Analyze image to record snapshot #1."
                  : "Each new analysis adds another snapshot (same product)."}
              </p>
            )}
          </div>

          {sessionLimitReached && (
            <div
              className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-3 text-sm text-amber-100"
              role="status"
            >
              <p className="font-medium">Session limit reached. Start a new session.</p>
              <p className="mt-1 text-xs leading-relaxed text-amber-100/85">
                Timeline is full ({MAX_SESSION_SNAPSHOTS} snapshots). You can still
                analyze images below—the result card, chat, compare, and graph use
                the latest analysis only.
              </p>
            </div>
          )}

          {session && summary.snapshotCount > 0 && (
            <div className="rounded-2xl border border-white/5 bg-slate-800/40 p-3 sm:p-4">
              <p className="mono-label mb-3 text-muted-foreground">Session summary</p>
              <div className="grid gap-3 text-sm sm:grid-cols-2">
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
                    {summary.bestConfidenceScore !== null && (
                      <span className="font-normal text-muted-foreground">
                        {" "}
                        ({Math.round(summary.bestConfidenceScore * 100)}%)
                      </span>
                    )}
                  </span>
                </p>
                <div className="text-muted-foreground sm:col-span-2">
                  <span>Confidence trend: </span>
                  <span
                    className="mt-1 inline-flex flex-wrap items-center gap-1.5"
                    aria-label="Confidence trend per snapshot"
                  >
                    {summary.confidenceTrends.map((trend, index) => (
                      <span
                        key={`trend-${index}`}
                        className="inline-flex items-center gap-0.5 rounded-full border border-white/10 bg-slate-900/60 px-1.5 py-0.5"
                        title={getTrendAriaLabel(trend)}
                      >
                        <span className="text-[10px] text-muted-foreground">
                          #{index + 1}
                        </span>
                        <TrendIcon trend={trend} />
                      </span>
                    ))}
                  </span>
                </div>
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
                <p className="mt-3 text-xs leading-relaxed text-amber-200/90">
                  Latest warnings: {summary.latestWarnings.join(" · ")}
                </p>
              )}
            </div>
          )}

          {session && session.snapshots.length > 0 && (
            <div>
              <p className="mono-label mb-2 text-muted-foreground">Snapshot timeline</p>
              <ol className="max-h-[min(50vh,360px)] space-y-2 overflow-y-auto pr-1">
                {session.snapshots.map((snapshot, index) => {
                  const trend = summary.confidenceTrends[index] ?? "neutral"
                  const analysis = snapshot.analysis
                  const isLatest = index === session.snapshots.length - 1
                  return (
                    <li
                      key={snapshot.localKey}
                      className={
                        isLatest
                          ? "rounded-2xl border border-violet-500/25 bg-violet-500/5 px-3 py-3 sm:px-4"
                          : "rounded-2xl border border-white/5 bg-slate-900/50 px-3 py-3 sm:px-4"
                      }
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-col gap-0.5 sm:flex-row sm:flex-wrap sm:items-baseline sm:gap-x-2">
                            <p className="text-xs font-semibold text-violet-200">
                              Snapshot #{snapshot.order}
                              {isLatest && (
                                <span className="ml-2 font-medium text-violet-300/90">
                                  Latest
                                </span>
                              )}
                            </p>
                            <p className="text-[11px] text-muted-foreground">
                              {formatSnapshotTime(snapshot.capturedAtMs)}
                            </p>
                          </div>
                          <p className="mt-1.5 break-words text-sm font-medium leading-snug text-foreground">
                            {analysis.product.display_name}
                          </p>
                          <p className="mt-0.5 break-words text-xs text-muted-foreground">
                            {analysis.product.category}
                          </p>
                        </div>
                        <div
                          className="flex shrink-0 flex-col items-center gap-0.5"
                          title={getTrendAriaLabel(trend)}
                        >
                          <TrendIcon trend={trend} />
                        </div>
                      </div>
                      <div className="mt-2.5 flex flex-wrap gap-1.5 text-[11px] leading-tight">
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-muted-foreground">
                          {formatConfidence(analysis)}
                        </span>
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-muted-foreground">
                          {getGroundingLabel(analysis.grounding_status)}
                        </span>
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-muted-foreground">
                          {analysis.warnings.length} warning
                          {analysis.warnings.length === 1 ? "" : "s"}
                        </span>
                        <span className="rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-muted-foreground">
                          {getModeLabel(analysis.mode)}
                          {analysis.cache_hit === true ? " · cached" : ""}
                        </span>
                      </div>
                    </li>
                  )
                })}
              </ol>
            </div>
          )}

          {session && session.snapshots.length === 0 && (
            <div className="rounded-2xl border border-dashed border-white/10 bg-slate-900/40 px-4 py-4 text-center">
              <p className="text-sm font-medium text-foreground">Session active</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                No snapshots yet. Use the camera or upload flow above, then analyze
                to add snapshot #1. Nothing is stored after you leave this page.
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
