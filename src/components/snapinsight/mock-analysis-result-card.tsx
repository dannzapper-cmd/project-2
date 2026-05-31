import { AlertTriangle, Clock, Database, ShieldCheck, Sparkles } from "lucide-react"

import type {
  AnalysisResponse,
  GroundingStatus,
  NutritionSummary,
} from "@/lib/snapinsight-api"

interface MockAnalysisResultCardProps {
  result: AnalysisResponse
}

function getModeLabel(mode: AnalysisResponse["mode"]): string {
  if (mode === "gemini") return "AI Analysis"
  if (mode === "mock_fallback") return "Mock Fallback"
  return "Mock (dev)"
}

function getModeBadgeClass(mode: AnalysisResponse["mode"]): string {
  if (mode === "gemini") {
    return "border-emerald-500/30 bg-emerald-500/15 text-emerald-300"
  }
  if (mode === "mock_fallback") {
    return "border-amber-500/30 bg-amber-500/15 text-amber-300"
  }
  return "border-white/10 bg-slate-800/70 text-muted-foreground"
}

function getGroundingLabel(status: GroundingStatus): string {
  if (status === "grounded") return "Grounded"
  if (status === "partial_match") return "Partial match"
  if (status === "grounding_unavailable") return "Source unavailable"
  return "No source match"
}

function getGroundingBadgeClass(status: GroundingStatus): string {
  if (status === "grounded") {
    return "border-emerald-500/30 bg-emerald-500/15 text-emerald-300"
  }
  if (status === "partial_match") {
    return "border-amber-500/30 bg-amber-500/15 text-amber-300"
  }
  return "border-white/10 bg-slate-800/70 text-muted-foreground"
}

function getGradeClass(grade: string): string {
  const normalized = grade.toUpperCase()
  if (normalized === "A") return "border-emerald-500/30 bg-emerald-500/15 text-emerald-300"
  if (normalized === "B") return "border-lime-500/30 bg-lime-500/15 text-lime-300"
  if (normalized === "C") return "border-yellow-500/30 bg-yellow-500/15 text-yellow-300"
  if (normalized === "D") return "border-orange-500/30 bg-orange-500/15 text-orange-300"
  return "border-red-500/30 bg-red-500/15 text-red-300"
}

function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`
}

function getGroundingMessage(result: AnalysisResponse): string | null {
  if (result.grounding_status === "no_match") {
    return "No reliable OpenFoodFacts match found. Try a photo showing the front label or barcode."
  }
  if (result.grounding_status === "grounding_unavailable") {
    return "Could not reach OpenFoodFacts. AI analysis above is still valid."
  }
  return result.grounding_summary || null
}

function getNutritionRows(summary: NutritionSummary | null | undefined) {
  if (!summary) return []

  return [
    ["Energy", summary.energy_kcal_100g, "kcal"],
    ["Sugars", summary.sugars_100g, "g"],
    ["Fat", summary.fat_100g, "g"],
    ["Saturated fat", summary.saturated_fat_100g, "g"],
    ["Protein", summary.proteins_100g, "g"],
    ["Salt", summary.salt_100g, "g"],
  ].filter((row): row is [string, string, string] => Boolean(row[1]))
}

export function MockAnalysisResultCard({ result }: MockAnalysisResultCardProps) {
  const groundingMessage = getGroundingMessage(result)
  const citationHeading =
    result.mode === "mock_fallback" && result.citations.length > 0
      ? "Source data (community)"
      : "Citations"
  const enrichment = result.product_enrichment
  const nutritionRows = getNutritionRows(enrichment?.nutrition_summary)
  const hasEnrichment = Boolean(
    enrichment &&
      (nutritionRows.length > 0 ||
        enrichment.nutrition_grade ||
        enrichment.labels.length > 0 ||
        enrichment.additives.length > 0)
  )

  return (
    <section className="glass-card mt-5 p-5" aria-live="polite">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${getModeBadgeClass(result.mode)}`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {getModeLabel(result.mode)}
        </span>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${getGroundingBadgeClass(result.grounding_status)}`}
        >
          <Database className="h-3.5 w-3.5" />
          {getGroundingLabel(result.grounding_status)}
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
        {result.product.brand && (
          <p className="mt-1 text-sm text-muted-foreground">
            Brand: {result.product.brand}
          </p>
        )}
      </div>

      {result.mode === "mock_fallback" && (
        <div className="mb-4 rounded-2xl border border-amber-500/25 bg-amber-500/10 p-3 text-sm text-amber-100">
          Gemini was unavailable. This result is not real AI analysis.
        </div>
      )}

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
          <Database className="h-4 w-4" />
          <h3 className="text-sm font-medium text-foreground">
            {citationHeading}
          </h3>
        </div>
        {result.citations.length > 0 ? (
          <div className="space-y-3">
            {result.citations.map((citation) => (
              <div key={`${citation.field}-${citation.value}`} className="text-sm">
                <p className="font-medium text-foreground">
                  {citation.field_label}
                </p>
                <p className="mt-1 leading-relaxed text-muted-foreground">
                  {citation.value}
                </p>
                {citation.url && (
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex text-xs font-medium text-violet-300 hover:text-violet-200"
                  >
                    View on OpenFoodFacts
                  </a>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            {groundingMessage ?? "Not connected yet"}
          </p>
        )}
        {groundingMessage && result.citations.length > 0 && (
          <p className="mt-3 text-xs text-muted-foreground">
            {groundingMessage}
          </p>
        )}
        <p className="mt-3 text-xs text-muted-foreground">
          OpenFoodFacts data is community-contributed and may be incomplete.
        </p>
      </div>

      {hasEnrichment && enrichment && (
        <div className="mb-4 rounded-2xl border border-white/5 bg-slate-800/40 p-3">
          <h3 className="mb-3 text-sm font-medium text-foreground">
            Product details
          </h3>

          {nutritionRows.length > 0 && (
            <div className="mb-4 grid gap-2 text-sm sm:grid-cols-2">
              {nutritionRows.map(([label, value, unit]) => (
                <div
                  key={label}
                  className="flex items-center justify-between rounded-xl bg-slate-900/50 px-3 py-2"
                >
                  <span className="text-muted-foreground">{label}</span>
                  <span className="font-medium text-foreground">
                    {value} {unit}
                  </span>
                </div>
              ))}
            </div>
          )}

          {enrichment.nutrition_grade && (
            <div className="mb-4">
              <p className="mono-label mb-2 text-muted-foreground">Nutri-Score</p>
              <span
                className={`inline-flex h-9 w-9 items-center justify-center rounded-full border text-sm font-semibold ${getGradeClass(enrichment.nutrition_grade)}`}
              >
                {enrichment.nutrition_grade}
              </span>
            </div>
          )}

          {enrichment.labels.length > 0 && (
            <div className="mb-4">
              <p className="mono-label mb-2 text-muted-foreground">Labels</p>
              <div className="flex flex-wrap gap-2">
                {enrichment.labels.slice(0, 5).map((label) => (
                  <span
                    key={label}
                    className="rounded-full border border-white/10 bg-slate-900/60 px-3 py-1 text-xs text-muted-foreground"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {enrichment.additives.length > 0 && (
            <div className="mb-4">
              <p className="mono-label mb-2 text-muted-foreground">Additives</p>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {enrichment.additives.slice(0, 8).map((additive) => (
                  <li key={additive}>{additive}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">
                Additive names sourced from OpenFoodFacts community data.
              </p>
            </div>
          )}

          {enrichment.enrichment_source_confidence === "medium" && (
            <p className="mb-3 text-xs text-muted-foreground">
              Source matched by product name. Verify with product label.
            </p>
          )}

          <p className="text-xs text-muted-foreground">
            Nutrition and label data from OpenFoodFacts. Community-contributed.
            May be incomplete.
          </p>
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
