"use client"

import Link from "next/link"
import { Lightbulb, ScanLine } from "lucide-react"

import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"
import { PreviewBanner } from "@/components/shared/preview-banner"
import { MockAnalysisResultCard } from "@/components/snapinsight/mock-analysis-result-card"
import { useAnalysisStorage } from "@/hooks/use-analysis-storage"

const PRIVACY_NOTE =
  "Analysis results are stored locally on this device as JSON only. Images are not saved."

function formatStoredAt(iso: string): string {
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

export function InsightsScreen() {
  const { latest: analysis, storedAt } = useAnalysisStorage()

  return (
    <div className="flex min-h-screen flex-col bg-background pb-24">
      <Header variant="default" />
      <PreviewBanner className="mb-2" />

      <main className="flex-1 px-5 py-4">
        {analysis ? (
          <div className="space-y-3">
            <div className="flex items-start gap-3 rounded-2xl border border-white/5 bg-slate-900/50 p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/15">
                <Lightbulb className="h-5 w-5 text-violet-300" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-foreground">
                  Latest product insights
                </h1>
                {storedAt && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    From your last scan · {formatStoredAt(storedAt)}
                  </p>
                )}
              </div>
            </div>

            <MockAnalysisResultCard result={analysis} />

            <p className="text-center text-xs text-muted-foreground">{PRIVACY_NOTE}</p>

            <Link
              href="/scan"
              className="flex w-full items-center justify-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/15 py-3 text-sm font-medium text-violet-200 hover:bg-violet-500/25"
            >
              <ScanLine className="h-4 w-4" />
              Scan another product
            </Link>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="glass-card max-w-sm p-8 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/15">
                <Lightbulb className="h-7 w-7 text-violet-400" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">Insights</h2>
              <p className="mb-6 text-sm leading-relaxed text-muted-foreground">
                Scan a product to see AI insights, warnings, citations, and grounding
                status here. Results stay on this device only.
              </p>
              <Link
                href="/scan"
                className="gradient-primary flex h-12 w-full items-center justify-center gap-2 rounded-full text-sm font-semibold text-white shadow-lg shadow-violet-500/20"
              >
                <ScanLine className="h-4 w-4" />
                Scan a product
              </Link>
            </div>
          </div>
        )}
      </main>

      <BottomNav activeTab="insights" />
    </div>
  )
}
