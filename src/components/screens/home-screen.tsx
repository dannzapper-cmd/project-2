"use client"

import { ScanLine, Upload, FlaskConical, Lock, CheckCircle, Layers } from "lucide-react"
import Link from "next/link"
import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"

const statusChips = [
  { label: "Private by default", icon: Lock },
  { label: "Evidence-backed", icon: CheckCircle },
  { label: "Confidence-aware", icon: Layers },
]

export function HomeScreen() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-24">
      <Header variant="default" />

      <main className="flex-1 flex flex-col px-5 py-4">
        {/* Main scan card */}
        <div className="glass-card p-6 flex flex-col items-center text-center mb-4">
          {/* Scan icon */}
          <div className="w-16 h-16 rounded-2xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center mb-5">
            <ScanLine className="w-7 h-7 text-violet-400" />
          </div>

          {/* Heading */}
          <h2 className="text-xl font-semibold text-foreground mb-2">
            Analyze a product
          </h2>

          {/* Subtext */}
          <p className="text-sm text-muted-foreground leading-relaxed mb-6">
            Ready to explore. Point your camera at a label to begin.
          </p>

          {/* Primary CTA */}
          <Link
            href="/scan"
            className="flex items-center justify-center gap-2 w-full h-12 gradient-primary rounded-full text-white font-semibold text-sm shadow-lg shadow-violet-500/20 hover:shadow-violet-500/35 transition-shadow touch-target"
          >
            <ScanLine className="w-4 h-4" />
            Scan Now
          </Link>
        </div>

        {/* Secondary action cards */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {/* Upload Image */}
          <button className="flex flex-col items-center justify-center gap-2 p-5 rounded-2xl border border-white/8 bg-slate-900/50 hover:bg-slate-800/60 transition-colors touch-target">
            <Upload className="w-6 h-6 text-slate-400" />
            <span className="text-sm font-medium text-foreground">Upload Image</span>
          </button>

          {/* Try Sample */}
          <Link 
            href="/result"
            className="flex flex-col items-center justify-center gap-2 p-5 rounded-2xl border border-white/8 bg-slate-900/50 hover:bg-slate-800/60 transition-colors touch-target"
          >
            <FlaskConical className="w-6 h-6 text-slate-400" />
            <span className="text-sm font-medium text-foreground">Try Sample</span>
          </Link>
        </div>

        {/* Status chips */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {statusChips.map((chip) => {
            const Icon = chip.icon
            return (
              <div
                key={chip.label}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-800/60 border border-white/5"
              >
                <Icon className="w-3.5 h-3.5 text-violet-400" />
                <span className="mono-label text-slate-400">{chip.label}</span>
              </div>
            )
          })}
        </div>
      </main>

      <BottomNav activeTab="scan" />
    </div>
  )
}
