import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"
import { PreviewBanner } from "@/components/shared/preview-banner"
import { Lightbulb } from "lucide-react"

export default function InsightsPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-24">
      <Header variant="default" />
      <PreviewBanner className="mb-2" />
      <main className="flex-1 flex flex-col items-center justify-center px-5 py-4">
        <div className="glass-card p-8 text-center max-w-sm">
          <div className="w-16 h-16 rounded-2xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center mx-auto mb-4">
            <Lightbulb className="w-7 h-7 text-violet-400" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">Insights</h2>
          <p className="text-sm text-muted-foreground">
            Planned: personalized product insights after real scan and analysis
            flows ship. This screen is a layout preview only.
          </p>
        </div>
      </main>
      <BottomNav activeTab="insights" />
    </div>
  )
}
