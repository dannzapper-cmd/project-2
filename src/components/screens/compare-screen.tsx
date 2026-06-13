"use client"

import { useCallback, useId, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { GitCompareArrows, Images, ScanLine } from "lucide-react"

import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"
import { PreviewBanner } from "@/components/shared/preview-banner"
import { ProductComparePanel } from "@/components/snapinsight/product-compare-panel"
import { analyzeImage, type AnalysisResponse } from "@/lib/snapinsight-api"
import { persistSuccessfulAnalysis } from "@/lib/analysis-storage"
import { getAnalysisServiceErrorMessage } from "@/lib/deployment-errors"
import { preprocessImageForUpload } from "@/lib/image-preprocess"
import { useAnalysisStorage } from "@/hooks/use-analysis-storage"
import { cn } from "@/lib/utils"

const PRIVACY_NOTE =
  "Compare uses saved analysis JSON only — no images are sent to the compare endpoint."

export function CompareScreen() {
  const fileInputId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { latest, history } = useAnalysisStorage()
  const [productAOverride, setProductAOverride] = useState<AnalysisResponse | null>(
    null
  )
  const [productBOverride, setProductBOverride] = useState<AnalysisResponse | null>(
    null
  )
  const [clearedA, setClearedA] = useState(false)
  const [clearedB, setClearedB] = useState(false)
  const [analyzeTarget, setAnalyzeTarget] = useState<"A" | "B" | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)

  const defaultSlots = useMemo(() => {
    if (!latest) return { a: null, b: null }
    const second = history.find(
      (item) => item.analysis.request_id !== latest.request_id
    )
    return { a: latest, b: second?.analysis ?? null }
  }, [history, latest])

  const productA = productAOverride ?? (clearedA ? null : defaultSlots.a)
  const productB = productBOverride ?? (clearedB ? null : defaultSlots.b)

  const historyOptions = useMemo(
    () =>
      history.map((item) => ({
        id: item.analysis.request_id,
        label: item.analysis.product.display_name,
      })),
    [history]
  )

  const handlePickFromHistory = useCallback(
    (slot: "A" | "B", requestId: string) => {
      const record = history.find((item) => item.analysis.request_id === requestId)
      if (!record) return
      if (slot === "A") {
        setProductAOverride(record.analysis)
        setClearedA(false)
      } else {
        setProductBOverride(record.analysis)
        setClearedB(false)
      }
    },
    [history]
  )

  const handleAnalyzeClick = useCallback((slot: "A" | "B") => {
    setAnalyzeTarget(slot)
    setAnalyzeError(null)
    fileInputRef.current?.click()
  }, [])

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      event.target.value = ""
      if (!file || !analyzeTarget) return

      setIsAnalyzing(true)
      setAnalyzeError(null)

      try {
        const processed = await preprocessImageForUpload(file)
        const result = await analyzeImage(processed)
        persistSuccessfulAnalysis(result)

        if (analyzeTarget === "A") {
          setProductAOverride(result)
          setClearedA(false)
        } else {
          setProductBOverride(result)
          setClearedB(false)
        }
      } catch (err) {
        setAnalyzeError(getAnalysisServiceErrorMessage(err))
      } finally {
        setIsAnalyzing(false)
        setAnalyzeTarget(null)
      }
    },
    [analyzeTarget]
  )

  const hasAnyData = Boolean(productA || productB || history.length > 0)

  return (
    <div className="flex min-h-screen flex-col bg-background pb-24">
      <Header variant="default" />
      <PreviewBanner className="mb-2" />

      <main className="flex-1 px-5 py-4">
        <input
          ref={fileInputRef}
          id={fileInputId}
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={(event) => void handleFileChange(event)}
          aria-label="Upload product image for comparison"
        />

        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-2xl border border-white/5 bg-slate-900/50 p-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/15">
              <GitCompareArrows className="h-5 w-5 text-violet-300" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">
                Compare products
              </h1>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                Product A uses your latest scan when available. Add Product B by
                analyzing another image or picking a recent result.
              </p>
            </div>
          </div>

          {!hasAnyData && (
            <div className="glass-card p-6 text-center">
              <p className="mb-4 text-sm text-muted-foreground">
                Scan at least one product to start comparing.
              </p>
              <Link
                href="/scan"
                className="gradient-primary inline-flex h-11 items-center justify-center gap-2 rounded-full px-6 text-sm font-semibold text-white"
              >
                <ScanLine className="h-4 w-4" />
                Go to scan
              </Link>
            </div>
          )}

          {hasAnyData && (
            <>
              <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-3">
                <p className="mono-label mb-3 text-muted-foreground">Add products</p>
                <div className="flex flex-wrap gap-2">
                  {(["A", "B"] as const).map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => handleAnalyzeClick(slot)}
                      disabled={isAnalyzing}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/15 px-3 py-1.5 text-xs font-medium text-violet-200 hover:bg-violet-500/25",
                        isAnalyzing && "cursor-not-allowed opacity-60"
                      )}
                    >
                      <Images className="h-3.5 w-3.5" />
                      {isAnalyzing && analyzeTarget === slot
                        ? "Analyzing…"
                        : `Analyze for ${slot}`}
                    </button>
                  ))}
                </div>
                {historyOptions.length > 0 && (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {(["A", "B"] as const).map((slot) => {
                      const result = slot === "A" ? productA : productB
                      return (
                        <label
                          key={slot}
                          className="block text-xs text-muted-foreground"
                        >
                          Recent for {slot}
                          <select
                            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/60 px-2 py-1.5 text-xs text-foreground"
                            value={result?.request_id ?? ""}
                            onChange={(event) => {
                              const value = event.target.value
                              if (value) handlePickFromHistory(slot, value)
                            }}
                          >
                            <option value="">Select…</option>
                            {historyOptions.map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      )
                    })}
                  </div>
                )}
              </div>

              {analyzeError && (
                <div
                  className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300"
                  role="alert"
                >
                  {analyzeError}
                </div>
              )}

              <ProductComparePanel
                currentResult={null}
                productA={productA}
                productB={productB}
                replacementPrompt={null}
                onSaveA={() => undefined}
                onSaveB={() => undefined}
                onClearA={() => {
                  setProductAOverride(null)
                  setClearedA(true)
                }}
                onClearB={() => {
                  setProductBOverride(null)
                  setClearedB(true)
                }}
                onReplaceA={() => undefined}
                onReplaceB={() => undefined}
                onKeepBoth={() => undefined}
              />

              <p className="text-center text-xs text-muted-foreground">
                {PRIVACY_NOTE}
              </p>
            </>
          )}
        </div>
      </main>

      <BottomNav activeTab="compare" />
    </div>
  )
}
