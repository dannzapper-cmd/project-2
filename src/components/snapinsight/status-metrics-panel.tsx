"use client"

import { useCallback, useState } from "react"
import {
  Activity,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  ShieldCheck,
} from "lucide-react"

import {
  getHealth,
  getMetricsSummary,
  type AnalysisResponse,
  type HealthResponse,
  type MetricsSummaryResponse,
} from "@/lib/snapinsight-api"
import { cn } from "@/lib/utils"

interface StatusMetricsPanelProps {
  latestResult: AnalysisResponse | null
  className?: string
}

const METRICS_PRIVACY_COPY =
  "Operational metrics only. No images, audio, chat history, or compare history are stored."

// A small, curated set of operational counters keeps the panel uncluttered.
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

function cacheLabel(cacheHit: boolean | null | undefined): string {
  if (cacheHit === true) return "Hit (served from cache)"
  if (cacheHit === false) return "Miss (freshly analyzed)"
  return "Not applicable"
}

function groundingLabel(status: AnalysisResponse["grounding_status"]): string {
  if (status === "grounded") return "Grounded"
  if (status === "partial_match") return "Partial match"
  if (status === "grounding_unavailable") return "Source unavailable"
  return "No source match"
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  )
}

export function StatusMetricsPanel({
  latestResult,
  className,
}: StatusMetricsPanelProps) {
  const [open, setOpen] = useState(false)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [metrics, setMetrics] = useState<MetricsSummaryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [unavailable, setUnavailable] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    setUnavailable(false)
    // Fetch independently so one failing call still shows partial status.
    const [healthResult, metricsResult] = await Promise.allSettled([
      getHealth(),
      getMetricsSummary(),
    ])

    if (healthResult.status === "fulfilled") {
      setHealth(healthResult.value)
    } else {
      setHealth(null)
    }
    if (metricsResult.status === "fulfilled") {
      setMetrics(metricsResult.value)
    } else {
      setMetrics(null)
    }
    if (
      healthResult.status === "rejected" &&
      metricsResult.status === "rejected"
    ) {
      setUnavailable(true)
    }
    setLoading(false)
  }, [])

  const handleToggle = useCallback(() => {
    setOpen((value) => {
      const next = !value
      // Lazily fetch the first time the panel is expanded.
      if (next && !health && !metrics && !loading) {
        void refresh()
      }
      return next
    })
  }, [health, metrics, loading, refresh])

  return (
    <section
      className={cn(
        "rounded-2xl border border-white/5 bg-slate-900/50",
        className
      )}
    >
      <button
        type="button"
        onClick={handleToggle}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Activity className="h-4 w-4 text-violet-300" />
          Status &amp; metrics
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {open && (
        <div className="space-y-4 border-t border-white/5 px-4 py-4 text-sm">
          <div className="flex items-center justify-between gap-2">
            <p className="mono-label text-muted-foreground">Backend</p>
            <button
              type="button"
              onClick={() => void refresh()}
              disabled={loading}
              className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-xs text-muted-foreground hover:bg-slate-800 disabled:opacity-50"
            >
              <RefreshCw
                className={cn("h-3 w-3", loading && "animate-spin")}
              />
              Refresh
            </button>
          </div>

          {unavailable ? (
            <p className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90">
              Metrics are unavailable right now. Analysis, chat, and compare are
              not affected.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="space-y-1.5 rounded-xl bg-slate-950/30 p-3 text-xs">
                <Row
                  label="Status"
                  value={health ? health.status : "unknown"}
                />
                <Row
                  label="Analysis mode"
                  value={health ? health.analysis_mode : "unknown"}
                />
                <Row
                  label="Gemini configured"
                  value={
                    health ? (health.gemini_configured ? "yes" : "no") : "unknown"
                  }
                />
                <Row
                  label="Cache"
                  value={
                    health ? (health.cache_enabled ? "enabled" : "disabled") : "unknown"
                  }
                />
              </div>

              {latestResult && (
                <div className="space-y-1.5 rounded-xl bg-slate-950/30 p-3 text-xs">
                  <p className="mono-label mb-1 text-muted-foreground">
                    Latest analysis
                  </p>
                  <Row
                    label="Cache"
                    value={cacheLabel(latestResult.cache_hit)}
                  />
                  <Row
                    label="Latency"
                    value={`${latestResult.meta.latency_ms} ms`}
                  />
                  <Row
                    label="Grounding"
                    value={groundingLabel(latestResult.grounding_status)}
                  />
                </div>
              )}

              {metrics && (
                <div className="rounded-xl bg-slate-950/30 p-3 text-xs">
                  <p className="mono-label mb-2 text-muted-foreground">
                    Operational counters
                  </p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {COUNTER_LABELS.map(([key, label]) => (
                      <Row
                        key={key}
                        label={label}
                        value={String(metrics.counters[key] ?? 0)}
                      />
                    ))}
                  </div>
                  {metrics.last_latency_ms !== null && (
                    <div className="mt-2 border-t border-white/5 pt-2">
                      <Row
                        label="Last latency"
                        value={`${metrics.last_latency_ms} ms`}
                      />
                      {metrics.average_latency_ms !== null && (
                        <Row
                          label="Avg latency"
                          value={`${metrics.average_latency_ms} ms`}
                        />
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <p className="flex items-start gap-1.5 text-xs leading-relaxed text-muted-foreground">
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-300" />
            {METRICS_PRIVACY_COPY}
          </p>
        </div>
      )}
    </section>
  )
}
