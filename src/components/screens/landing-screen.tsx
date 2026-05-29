"use client"

import { ScanLine, Sparkles } from "lucide-react"
import Link from "next/link"

export function LandingScreen() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Top logo */}
      <header className="flex items-center gap-2 px-5 py-4 safe-area-top">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-violet-500/20">
          <Sparkles className="w-4 h-4 text-violet-400" />
        </div>
        <span className="text-violet-400 font-semibold tracking-tight">SnapInsight</span>
      </header>

      {/* Hero section */}
      <main className="flex-1 flex flex-col px-5 pb-8">
        {/* Phone scanning hero card */}
        <div className="relative w-full aspect-[4/5] max-w-[340px] mx-auto glass-card overflow-hidden mb-8">
          {/* Background gradient */}
          <div className="absolute inset-0 bg-gradient-to-b from-slate-800/50 to-slate-900/80" />
          
          {/* Viewfinder bracket container */}
          <div className="absolute inset-8 flex items-center justify-center">
            {/* Corner brackets */}
            <div className="relative w-full h-full">
              {/* Top-left bracket */}
              <div className="absolute top-0 left-0 w-6 h-6 border-l-2 border-t-2 border-violet-500 rounded-tl-lg" />
              {/* Top-right bracket */}
              <div className="absolute top-0 right-0 w-6 h-6 border-r-2 border-t-2 border-violet-500 rounded-tr-lg" />
              {/* Bottom-left bracket */}
              <div className="absolute bottom-0 left-0 w-6 h-6 border-l-2 border-b-2 border-violet-500 rounded-bl-lg" />
              {/* Bottom-right bracket */}
              <div className="absolute bottom-0 right-0 w-6 h-6 border-r-2 border-b-2 border-violet-500 rounded-br-lg" />
              
              {/* Phone with product mockup */}
              <div className="absolute inset-6 flex items-center justify-center">
                <div className="relative w-32 h-56 bg-slate-800 rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
                  {/* Phone screen */}
                  <div className="absolute inset-2 bg-slate-900 rounded-2xl flex items-center justify-center">
                    {/* Product package placeholder */}
                    <div className="w-16 h-24 bg-gradient-to-br from-amber-600/40 to-amber-800/40 rounded-lg border border-amber-500/20 flex items-center justify-center">
                      <div className="text-amber-400/60 text-[8px] font-medium">PRODUCT</div>
                    </div>
                  </div>
                  {/* Phone notch */}
                  <div className="absolute top-3 left-1/2 -translate-x-1/2 w-12 h-4 bg-slate-800 rounded-full" />
                </div>
              </div>

              {/* Analyzing chip */}
              <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/90 border border-white/10 rounded-full">
                <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-pulse" />
                <span className="mono-label text-violet-400">Analyzing...</span>
              </div>
            </div>
          </div>
          
          {/* Hand illustration placeholder */}
          <div className="absolute bottom-0 right-4 w-24 h-32 opacity-60">
            <div className="w-full h-full bg-gradient-to-t from-slate-700/30 to-transparent rounded-t-full" />
          </div>
        </div>

        {/* Headline */}
        <h1 className="text-3xl font-bold text-foreground text-center leading-tight mb-4">
          <span className="block">Point. Ask.</span>
          <span className="block text-violet-400">Understand.</span>
        </h1>

        {/* Subtext */}
        <p className="text-muted-foreground text-center text-sm leading-relaxed mb-8 max-w-[280px] mx-auto">
          A visual AI companion for understanding products with evidence, confidence, and clear explanations.
        </p>

        {/* CTAs */}
        <div className="flex flex-col gap-3 w-full max-w-[320px] mx-auto mt-auto">
          {/* Primary CTA */}
          <Link
            href="/home"
            className="flex items-center justify-center gap-2 w-full h-14 gradient-primary rounded-full text-white font-semibold text-base shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-shadow touch-target"
          >
            <ScanLine className="w-5 h-5" />
            Start scan
          </Link>

          {/* Secondary CTA */}
          <Link
            href="/result"
            className="flex items-center justify-center w-full h-14 bg-transparent border border-white/10 rounded-full text-foreground font-medium text-base hover:bg-white/5 transition-colors touch-target"
          >
            Try sample product
          </Link>
        </div>
      </main>
    </div>
  )
}
