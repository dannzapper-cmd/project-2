"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import {
  Activity,
  RefreshCw,
  ScanLine,
  ShieldCheck,
  Waves,
} from "lucide-react"

import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"
import { PreviewBanner } from "@/components/shared/preview-banner"
import {
  getGeminiLiveConfig,
  getHealth,
  getMetricsSummary,
  type GeminiLiveConfigResponse,
  type HealthResponse,
  type MetricsSummaryResponse,
} from "@/lib/snapinsight-api"
import { useAnalysisStorage } from "@/hooks/use-analysis-storage"
import type { AnalysisActivityEntry } from "@/lib/analysis-storage"
import { cn } from "@/lib/utils"

const METRICS_PRIVACY_COPY =
  "Operational metrics only. No images, audio, chat history, or compare history are stored on the server."

const COUNTER_LABELS: Array<[string, string]> = [
  ["total_analysis_requests", "Analyses"],
  ["cache_hits", "Cache hits"],
  ["cache_misses", "Cache misses"],
  ["gemini_requests", "Gemini"],
  ["mock_requests", "Mock"],
  ["analysis_errors", "Errors"],
  ["chat_requests", "Chat"],
  ["compare_requests", "Compare"],
]

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  )
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const rem = minutes % 60
  return rem > 0 ? `${hours}h ${rem}m` : `${hours}h`
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  } catch {
    return iso
  }
}

function groundingLabel(status: AnalysisActivityEntry["grounding_status"]): string {
  if (status === "grounded") return "Grounded"
  if (status === "partial_match") return "Partial match"
  if (status === "grounding_unavailable") return "Source unavailable"
  return "No source match"
}

function liveConfigLabel(config: GeminiLiveConfigResponse | null): string {
  if (!config) return "Unknown"
  if (config.status === "disabled") return "Disabled"
  if (config.status === "not_configured") return "Not configured"
  if (config.requires_access_code) return "Requires access code"
  return "Ready"
}

function cacheLabel(cacheHit: boolean | null): string {
  if (cacheHit === true) return "Cache hit"
  if (cacheHit === false) return "Fresh analysis"
  return "N/A"
}

export function ActivityScreen() {
  const { activity: localActivity } = useAnalysisStorage()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [metrics, setMetrics] = useState<MetricsSummaryResponse | null>(null)
  const [liveConfig, setLiveConfig] = useState<GeminiLiveConfigResponse | null>(
    null
  )
  const [loading, setLoading] = useState(true)
  const [unavailable, setUnavailable] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    setUnavailable(false)

    const [healthResult, metricsResult, liveResult] = await Promise.allSettled([
      getHealth(),
      getMetricsSummary(),
      getGeminiLiveConfig(),
    ])

    if (healthResult.status === "fulfilled") setHealth(healthResult.value)
    else setHealth(null)

    if (metricsResult.status === "fulfilled") setMetrics(metricsResult.value)
    else setMetrics(null)

    if (liveResult.status === "fulfilled") setLiveConfig(liveResult.value)
    else setLiveConfig(null)

    if (
      healthResult.status === "rejected" &&
      metricsResult.status === "rejected"
    ) {
      setUnavailable(true)
    }

    setLoading(false)
  }, [])

  useEffect(() => {
    let active = true

    async function loadMetrics() {
      setLoading(true)
      setUnavailable(false)

      const [healthResult, metricsResult, liveResult] = await Promise.allSettled([
        getHealth(),
        getMetricsSummary(),
        getGeminiLiveConfig(),
      ])

      if (!active) return

      if (healthResult.status === "fulfilled") setHealth(healthResult.value)
      else setHealth(null)

      if (metricsResult.status === "fulfilled") setMetrics(metricsResult.value)
      else setMetrics(null)

      if (liveResult.status === "fulfilled") setLiveConfig(liveResult.value)
      else setLiveConfig(null)

      if (
        healthResult.status === "rejected" &&
        metricsResult.status === "rejected"
      ) {
        setUnavailable(true)
      }

      setLoading(false)
    }

    void loadMetrics()

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="flex min-h-screen flex-col bg-background pb-24">
      <Header variant="default" />
      <PreviewBanner className="mb-2" />

      <main className="flex-1 space-y-4 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/15">
              <Activity className="h-5 w-5 text-violet-300" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">Activity</h1>
              <p className="mt-1 text-xs text-muted-foreground">
                Backend metrics and your local scan activity on this device.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
            className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
            Refresh
          </button>
        </div>

        {unavailable ? (
          <div className="glass-card p-4">
            <p className="text-sm text-amber-100/90">
              Backend metrics are unavailable right now. Your local scan history
              below is still available on this device.
            </p>
          </div>
        ) : (
          <>
            <section className="glass-card space-y-3 p-4 text-sm">
              <p className="mono-label text-muted-foreground">Backend status</p>
              <div className="space-y-1.5 rounded-xl bg-slate-950/30 p-3 text-xs">
                <Row label="Status" value={health?.status ?? "unknown"} />
                <Row
                  label="Analysis mode"
                  value={health?.analysis_mode ?? "unknown"}
                />
                <Row
                  label="Gemini configured"
                  value={
                    health
                      ? health.gemini_configured
                        ? "yes"
                        : "no"
                      : "unknown"
                  }
                />
                <Row
                  label="Cache"
                  value={
                    health
                      ? health.cache_enabled
                        ? "enabled"
                        : "disabled"
                      : "unknown"
                  }
                />
                <Row
                  label="Mock fallback"
                  value={
                    health
                      ? health.mock_fallback_allowed
                        ? "allowed"
                        : "disabled"
                      : "unknown"
                  }
                />
                {metrics && (
                  <Row
                    label="Uptime"
                    value={formatUptime(metrics.uptime_seconds)}
                  />
                )}
              </div>
            </section>

            {metrics && (
              <section className="glass-card space-y-3 p-4 text-sm">
                <p className="mono-label text-muted-foreground">Latency</p>
                <div className="space-y-1.5 rounded-xl bg-slate-950/30 p-3 text-xs">
                  <Row
                    label="Last latency"
                    value={
                      metrics.last_latency_ms !== null
                        ? `${metrics.last_latency_ms} ms`
                        : "—"
                    }
                  />
                  <Row
                    label="Average latency"
                    value={
                      metrics.average_latency_ms !== null
                        ? `${metrics.average_latency_ms} ms`
                        : "—"
                    }
                  />
                </div>
              </section>
            )}

            {metrics && (
              <section className="glass-card space-y-3 p-4 text-sm">
                <p className="mono-label text-muted-foreground">
                  Operational counters
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-xl bg-slate-950/30 p-3 text-xs">
                  {COUNTER_LABELS.map(([key, label]) => (
                    <Row
                      key={key}
                      label={label}
                      value={String(metrics.counters[key] ?? 0)}
                    />
                  ))}
                </div>
              </section>
            )}

            {metrics && (
              <section className="glass-card space-y-3 p-4 text-sm">
                <p className="mono-label text-muted-foreground">Usage limits</p>
                <div className="space-y-1.5 rounded-xl bg-slate-950/30 p-3 text-xs">
                  <Row
                    label="Daily analysis limit"
                    value={String(
                      metrics.usage_limits_daily_analysis_limit ?? "—"
                    )}
                  />
                  <Row
                    label="Daily estimated cost"
                    value={
                      metrics.usage_limits_daily_estimated_cost_usd !== null &&
                      metrics.usage_limits_daily_estimated_cost_usd !== undefined
                        ? `$${metrics.usage_limits_daily_estimated_cost_usd}`
                        : "—"
                    }
                  />
                  <Row
                    label="Max analyses / session"
                    value={String(
                      metrics.usage_limits_max_analyses_per_session ?? "—"
                    )}
                  />
                  <Row
                    label="Max chat messages / session"
                    value={String(
                      metrics.usage_limits_max_chat_messages_per_session ?? "—"
                    )}
                  />
                  <Row
                    label="Max compare / session"
                    value={String(
                      metrics.usage_limits_max_compare_per_session ?? "—"
                    )}
                  />
                </div>
              </section>
            )}

            <section className="glass-card space-y-3 p-4 text-sm">
              <div className="flex items-center gap-2">
                <Waves className="h-4 w-4 text-violet-300" />
                <p className="mono-label text-muted-foreground">Gemini Live</p>
              </div>
              <div className="space-y-1.5 rounded-xl bg-slate-950/30 p-3 text-xs">
                <Row label="Status" value={liveConfigLabel(liveConfig)} />
                {liveConfig?.model && (
                  <Row label="Model" value={liveConfig.model} />
                )}
                {liveConfig && (
                  <Row
                    label="Max session"
                    value={`${liveConfig.max_session_seconds}s`}
                  />
                )}
              </div>
            </section>
          </>
        )}

        <section className="glass-card space-y-3 p-4 text-sm">
          <p className="mono-label text-muted-foreground">
            Local scan activity (this browser)
          </p>
          {localActivity.length === 0 ? (
            <div className="rounded-xl bg-slate-950/30 p-4 text-center">
              <p className="text-xs text-muted-foreground">
                No scans recorded in this session yet.
              </p>
              <Link
                href="/scan"
                className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-violet-300 hover:text-violet-200"
              >
                <ScanLine className="h-3.5 w-3.5" />
                Scan a product
              </Link>
            </div>
          ) : (
            <ul className="space-y-2">
              {localActivity.map((entry) => (
                <li
                  key={entry.id}
                  className="rounded-xl border border-white/5 bg-slate-950/30 p-3 text-xs"
                >
                  <p className="font-medium text-foreground">
                    {entry.product_name}
                  </p>
                  <p className="mt-1 text-muted-foreground">
                    {formatTimestamp(entry.timestamp)} · {entry.model} ·{" "}
                    {entry.latency_ms} ms · {entry.confidence_label} (
                    {Math.round(entry.confidence_score * 100)}%)
                  </p>
                  <p className="mt-1 text-muted-foreground">
                    {groundingLabel(entry.grounding_status)} ·{" "}
                    {cacheLabel(entry.cache_hit)}
                  </p>
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs leading-relaxed text-muted-foreground">
            Local activity is metadata only — no images stored. Cleared when you
            close this browser tab/session.
          </p>
        </section>

        <p className="flex items-start gap-1.5 text-xs leading-relaxed text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-300" />
          {METRICS_PRIVACY_COPY}
        </p>
      </main>

      <BottomNav activeTab="activity" />
    </div>
  )
}
