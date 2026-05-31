"use client"

import { useCallback, useState } from "react"
import { AlertTriangle, Database, GitCompareArrows, X } from "lucide-react"

import {
  compareProducts,
  type AnalysisCitation,
  type AnalysisResponse,
  type CompareFieldDiff,
  type CompareProductsResponse,
  type CompareStatus,
} from "@/lib/snapinsight-api"
import { cn } from "@/lib/utils"

interface ProductComparePanelProps {
  currentResult: AnalysisResponse | null
  productA: AnalysisResponse | null
  productB: AnalysisResponse | null
  replacementPrompt: AnalysisResponse | null
  onSaveA: (result: AnalysisResponse) => void
  onSaveB: (result: AnalysisResponse) => void
  onClearA: () => void
  onClearB: () => void
  onReplaceA: () => void
  onReplaceB: () => void
  onKeepBoth: () => void
}

const GROUPS = [
  {
    title: "Product",
    fields: ["product_name", "brand", "category"],
  },
  {
    title: "Grounding",
    fields: ["grounding_status", "grounding_summary", "match_method"],
  },
  {
    title: "Nutrition",
    fields: [
      "energy_kcal_100g",
      "sugars_100g",
      "fat_100g",
      "saturated_fat_100g",
      "proteins_100g",
      "salt_100g",
      "nutrition_grade",
    ],
  },
  {
    title: "Labels",
    fields: ["labels"],
  },
  {
    title: "Additives",
    fields: ["additives"],
  },
  {
    title: "Warnings / uncertainty",
    fields: ["warnings"],
  },
]

function statusLabel(status: CompareStatus): string {
  if (status === "same") return "Same"
  if (status === "different") return "Different"
  if (status === "missing_a") return "Missing A"
  if (status === "missing_b") return "Missing B"
  return "Missing both"
}

function statusClass(status: CompareStatus): string {
  if (status === "same") {
    return "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
  }
  if (status === "different") {
    return "border-violet-500/25 bg-violet-500/10 text-violet-200"
  }
  return "border-amber-500/25 bg-amber-500/10 text-amber-100"
}

function valueText(value: string | null): string {
  return value && value.trim() ? value : "Missing"
}

function slotTitle(result: AnalysisResponse | null): string {
  return result?.product.display_name || "Empty slot"
}

function hasLimitedSource(result: AnalysisResponse | null): boolean {
  return (
    result?.grounding_status === "no_match" ||
    result?.grounding_status === "grounding_unavailable"
  )
}

function hasPartialMatch(result: AnalysisResponse | null): boolean {
  return result?.grounding_status === "partial_match"
}

function citationKey(citation: AnalysisCitation): string {
  return `${citation.source}-${citation.field}-${citation.url}-${citation.value}`
}

function groupedDifferences(
  differences: CompareFieldDiff[],
  fields: string[]
): CompareFieldDiff[] {
  return fields
    .map((field) => differences.find((difference) => difference.field === field))
    .filter((difference): difference is CompareFieldDiff => Boolean(difference))
}

export function ProductComparePanel({
  currentResult,
  productA,
  productB,
  replacementPrompt,
  onSaveA,
  onSaveB,
  onClearA,
  onClearB,
  onReplaceA,
  onReplaceB,
  onKeepBoth,
}: ProductComparePanelProps) {
  const [comparisonState, setComparisonState] = useState<{
    slotKey: string
    response: CompareProductsResponse
  } | null>(null)
  const [errorState, setErrorState] = useState<{
    slotKey: string
    message: string
  } | null>(null)
  const [isComparing, setIsComparing] = useState(false)
  const slotKey = `${productA?.request_id ?? "empty"}:${productB?.request_id ?? "empty"}`
  const comparison =
    comparisonState?.slotKey === slotKey ? comparisonState.response : null
  const error = errorState?.slotKey === slotKey ? errorState.message : null

  const runCompare = useCallback(async () => {
    if (!productA || !productB || isComparing) return
    setIsComparing(true)
    setErrorState(null)

    try {
      const result = await compareProducts(productA, productB)
      setComparisonState({ slotKey, response: result })
    } catch (err) {
      setErrorState({
        slotKey,
        message:
          err instanceof Error ? err.message : "Compare is unavailable right now.",
      })
    } finally {
      setIsComparing(false)
    }
  }, [isComparing, productA, productB, slotKey])

  const canCompare = Boolean(productA && productB)
  const sourceLimited = hasLimitedSource(productA) || hasLimitedSource(productB)
  const partialMatch = hasPartialMatch(productA) || hasPartialMatch(productB)
  const slots = [
    {
      label: "A",
      result: productA,
      onClear: onClearA,
      onSave: () => currentResult && onSaveA(currentResult),
    },
    {
      label: "B",
      result: productB,
      onClear: onClearB,
      onSave: () => currentResult && onSaveB(currentResult),
    },
  ]

  return (
    <section className="glass-card mt-5 p-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/15">
          <GitCompareArrows className="h-5 w-5 text-violet-300" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            Compare two analyzed products.
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Analysis is based on available source data. Verify physical labels.
          </p>
          {partialMatch && (
            <p className="mt-2 text-xs text-amber-100/80">
              One product was matched by name. Verify with the label.
            </p>
          )}
          {sourceLimited && (
            <p className="mt-2 text-xs text-amber-100/80">
              Source data is limited for one product.
            </p>
          )}
        </div>
      </div>

      {replacementPrompt && (
        <div className="mb-4 rounded-2xl border border-violet-500/20 bg-violet-500/10 p-3">
          <p className="text-sm text-violet-100">
            Replace Product A or Product B with this result?
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onReplaceA}
              className="rounded-full border border-violet-500/30 bg-violet-500/15 px-3 py-1.5 text-xs font-medium text-violet-200 hover:bg-violet-500/25"
            >
              Replace A
            </button>
            <button
              type="button"
              onClick={onReplaceB}
              className="rounded-full border border-violet-500/30 bg-violet-500/15 px-3 py-1.5 text-xs font-medium text-violet-200 hover:bg-violet-500/25"
            >
              Replace B
            </button>
            <button
              type="button"
              onClick={onKeepBoth}
              className="rounded-full border border-white/10 bg-slate-900/60 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-slate-800/80"
            >
              Keep both
            </button>
          </div>
        </div>
      )}

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        {slots.map(({ label, result, onClear, onSave }) => (
          <div
            key={label}
            className="rounded-2xl border border-white/5 bg-slate-900/50 p-3"
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="mono-label text-muted-foreground">Product {label}</p>
              {result && (
                <button
                  type="button"
                  onClick={onClear}
                  className="rounded-full p-1 text-muted-foreground hover:bg-white/5 hover:text-foreground"
                  aria-label={`Clear Product ${label}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <p className="min-h-10 text-sm font-medium text-foreground">
              {slotTitle(result)}
            </p>
            {currentResult && (
              <button
                type="button"
                onClick={onSave}
                className="mt-3 rounded-full border border-white/10 bg-slate-800/70 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-slate-800"
              >
                Save current as {label}
              </button>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={() => void runCompare()}
        disabled={!canCompare || isComparing}
        className={cn(
          "touch-target w-full rounded-full border border-violet-500/30 bg-violet-500/15 px-4 py-2 text-sm font-medium text-violet-200 hover:bg-violet-500/25",
          (!canCompare || isComparing) &&
            "cursor-not-allowed opacity-60 hover:bg-violet-500/15"
        )}
      >
        {isComparing ? "Comparing..." : "Compare products"}
      </button>

      {!canCompare && (
        <p className="mt-3 text-center text-xs text-muted-foreground">
          Save two analyzed products to compare available fields.
        </p>
      )}

      {error && (
        <div className="mt-4 rounded-2xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {comparison && (
        <div className="mt-5 space-y-4">
          <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-4">
            <p className="text-sm leading-relaxed text-foreground">
              {comparison.summary}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Request ID: {comparison.request_id} · {comparison.latency_ms}ms
            </p>
          </div>

          {GROUPS.map((group) => {
            const rows = groupedDifferences(comparison.differences, group.fields)
            if (rows.length === 0) return null

            return (
              <div
                key={group.title}
                className="rounded-2xl border border-white/5 bg-slate-800/40 p-3"
              >
                <h3 className="mb-3 text-sm font-medium text-foreground">
                  {group.title}
                </h3>
                <div className="space-y-3">
                  {rows.map((difference) => (
                    <div
                      key={difference.field}
                      className="rounded-xl bg-slate-950/30 p-3 text-sm"
                    >
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <p className="font-medium text-foreground">
                          {difference.label}
                        </p>
                        <span
                          className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${statusClass(difference.status)}`}
                        >
                          {statusLabel(difference.status)}
                        </span>
                      </div>
                      <div className="grid gap-2 text-xs sm:grid-cols-2">
                        <p className="text-muted-foreground">
                          <span className="font-medium text-slate-300">A:</span>{" "}
                          {valueText(difference.product_a_value)}
                        </p>
                        <p className="text-muted-foreground">
                          <span className="font-medium text-slate-300">B:</span>{" "}
                          {valueText(difference.product_b_value)}
                        </p>
                      </div>
                      {difference.note && (
                        <p className="mt-2 text-xs text-muted-foreground">
                          {difference.note}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          {comparison.citations_used.length > 0 && (
            <div className="rounded-2xl border border-white/5 bg-slate-800/40 p-3">
              <div className="mb-2 flex items-center gap-2 text-muted-foreground">
                <Database className="h-4 w-4" />
                <h3 className="text-sm font-medium text-foreground">
                  Sources used
                </h3>
              </div>
              <div className="space-y-2">
                {comparison.citations_used.map((citation) => (
                  <div key={citationKey(citation)} className="text-sm">
                    <p className="font-medium text-foreground">
                      {citation.field_label}
                    </p>
                    <p className="text-muted-foreground">{citation.value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {comparison.warnings.length > 0 && (
            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-3">
              <div className="mb-2 flex items-center gap-2 text-amber-200">
                <AlertTriangle className="h-4 w-4" />
                <h3 className="text-sm font-medium">Warnings</h3>
              </div>
              <ul className="list-disc space-y-1 pl-5 text-xs text-amber-100/80">
                {comparison.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
