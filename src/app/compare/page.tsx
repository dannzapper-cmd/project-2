import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"
import { GitCompareArrows } from "lucide-react"

export default function ComparePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-24">
      <Header variant="default" />
      <main className="flex-1 flex flex-col items-center justify-center px-5 py-4">
        <div className="glass-card p-8 text-center max-w-sm">
          <div className="w-16 h-16 rounded-2xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center mx-auto mb-4">
            <GitCompareArrows className="w-7 h-7 text-violet-400" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">Compare</h2>
          <p className="text-sm text-muted-foreground">
            Compare products side-by-side to make informed decisions.
          </p>
        </div>
      </main>
      <BottomNav activeTab="compare" />
    </div>
  )
}
