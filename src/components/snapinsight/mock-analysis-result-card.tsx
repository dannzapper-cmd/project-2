import { AlertTriangle, Clock, Database, ShieldCheck, Sparkles } from "lucide-react"

import type { AnalysisResponse } from "@/lib/snapinsight-api"

interface MockAnalysisResultCardProps {
  result: AnalysisResponse
}

function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`
}

export function MockAnalysisResultCard({ result }: MockAnalysisResultCardProps) {
  return (
    <section className="glass-card mt-5 p-5" aria-live="polite">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/15 px-3 py-1 text-xs font-medium text-violet-300">
          <Sparkles className="h-3.5 w-3.5" />
          Mock analysis / no AI yet
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-slate-800/70 px-3 py-1 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          {result.meta.latency_ms}ms
        </span>
      </div>

      <div className="mb-4">
        <h2 className="text-xl font-semibold text-foreground">
          {result.product.display_name}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Category: {result.product.category}
        </p>
      </div>

      <div className="mb-4 grid gap-3 rounded-2xl border border-white/5 bg-slate-900/50 p-4 text-sm sm:grid-cols-2">
        <div>
          <p className="mono-label mb-1 text-muted-foreground">Confidence</p>
          <p className="font-medium text-foreground">
            {result.product.confidence.label} -{" "}
            {formatScore(result.product.confidence.score)}
          </p>
        </div>
        <div>
          <p className="mono-label mb-1 text-muted-foreground">Model</p>
          <p className="font-medium text-foreground">{result.meta.model}</p>
        </div>
      </div>

      {result.insights.length > 0 && (
        <div className="mb-4">
          <h3 className="mono-label mb-2 text-muted-foreground">Insights</h3>
          <div className="space-y-2">
            {result.insights.map((insight) => (
              <div
                key={`${insight.type}-${insight.title}`}
                className="rounded-2xl border border-white/5 bg-slate-800/40 p-3"
              >
                <p className="text-sm font-medium text-foreground">
                  {insight.title}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  {insight.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="mb-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 p-3">
          <div className="mb-2 flex items-center gap-2 text-amber-300">
            <AlertTriangle className="h-4 w-4" />
            <h3 className="text-sm font-medium">Warnings</h3>
          </div>
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-100/80">
            {result.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mb-4 rounded-2xl border border-white/5 bg-slate-800/40 p-3">
        <div className="mb-2 flex items-center gap-2 text-muted-foreground">
          <ShieldCheck className="h-4 w-4" />
          <h3 className="text-sm font-medium text-foreground">Privacy</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Image stored: {result.privacy.image_stored ? "yes" : "no"} - Retention:{" "}
          {result.privacy.image_retention}
        </p>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Database className="h-3.5 w-3.5" />
        <span>Request ID: {result.request_id}</span>
      </div>
    </section>
  )
}
