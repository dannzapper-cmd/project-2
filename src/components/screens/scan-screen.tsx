"use client"

import { Images, Zap } from "lucide-react"
import Link from "next/link"
import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"

const detectionTags = [
  { label: "Brand detected", top: "22%", left: "50%", translateX: "-50%" },
  { label: "Ingredients", top: "48%", left: "15%" },
  { label: "Nutrition Facts", top: "68%", left: "55%" },
]

export function ScanScreen() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-24">
      <Header variant="default" />

      <main className="flex-1 flex flex-col px-5 py-4">
        {/* Viewfinder area */}
        <div className="relative flex-1 min-h-[400px] max-h-[500px] rounded-3xl overflow-hidden bg-gradient-to-b from-slate-800/40 to-slate-900/60">
          {/* Corner brackets */}
          <div className="absolute inset-4">
            {/* Top-left bracket */}
            <div className="absolute top-0 left-0 w-8 h-8 border-l-2 border-t-2 border-violet-500 rounded-tl-xl" />
            {/* Top-right bracket */}
            <div className="absolute top-0 right-0 w-8 h-8 border-r-2 border-t-2 border-violet-500 rounded-tr-xl" />
            {/* Bottom-left bracket */}
            <div className="absolute bottom-0 left-0 w-8 h-8 border-l-2 border-b-2 border-violet-500 rounded-bl-xl" />
            {/* Bottom-right bracket */}
            <div className="absolute bottom-0 right-0 w-8 h-8 border-r-2 border-b-2 border-violet-500 rounded-br-xl" />
          </div>

          {/* Processing status */}
          <div className="absolute top-8 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 bg-slate-800/90 border border-white/10 rounded-full z-10">
            <div className="w-2 h-2 bg-violet-500 rounded-full animate-pulse" />
            <span className="mono-label text-slate-300">Processing</span>
          </div>

          {/* Detection tags */}
          {detectionTags.map((tag) => (
            <div
              key={tag.label}
              className="absolute px-4 py-2 bg-slate-800/85 backdrop-blur-sm border border-white/10 rounded-full"
              style={{
                top: tag.top,
                left: tag.left,
                transform: tag.translateX ? `translateX(${tag.translateX})` : undefined,
              }}
            >
              <span className="text-sm text-slate-200 font-medium">{tag.label}</span>
            </div>
          ))}

          {/* Simulated scan area */}
          <div className="absolute inset-12 border border-dashed border-white/10 rounded-2xl" />
        </div>

        {/* Capture controls */}
        <div className="flex items-center justify-center gap-8 py-6">
          {/* Gallery button */}
          <button className="flex items-center justify-center w-12 h-12 rounded-full bg-slate-800/80 border border-white/10 hover:bg-slate-700/80 transition-colors touch-target">
            <Images className="w-5 h-5 text-slate-400" />
          </button>

          {/* Capture button */}
          <Link
            href="/result"
            className="flex items-center justify-center w-16 h-16 rounded-full bg-violet-400 hover:bg-violet-300 transition-colors shadow-lg shadow-violet-500/30 touch-target"
          >
            <div className="w-14 h-14 rounded-full border-2 border-slate-900/30" />
          </Link>

          {/* Flash button */}
          <button className="flex items-center justify-center w-12 h-12 rounded-full bg-slate-800/80 border border-white/10 hover:bg-slate-700/80 transition-colors touch-target">
            <Zap className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Privacy note */}
        <p className="text-xs text-muted-foreground text-center">
          Images are used only for this analysis.
        </p>
      </main>

      <BottomNav activeTab="scan" />
    </div>
  )
}
