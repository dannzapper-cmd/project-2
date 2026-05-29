"use client"

import {
  CheckCircle,
  Sparkles,
  List,
  AlertTriangle,
  Activity,
  FlaskConical,
  GitCompareArrows,
  Leaf,
  Database,
  HelpCircle,
  Check,
} from "lucide-react"
import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"
import { PreviewBanner } from "@/components/shared/preview-banner"
import { mockProduct } from "@/lib/mock-data"

export function ResultScreen() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-28">
      <Header variant="back" />
      <PreviewBanner className="mb-2" />

      <main className="flex-1 flex flex-col overflow-y-auto px-5 py-2">
        {/* Confidence badge */}
        <div className="flex items-center gap-2 mb-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-500/15 border border-violet-500/30 rounded-full">
            <CheckCircle className="w-3.5 h-3.5 text-violet-400" />
            <span className="mono-label text-violet-400">{mockProduct.confidence}</span>
          </div>
        </div>

        {/* Product title */}
        <h1 className="text-2xl font-bold text-foreground mb-4">
          {mockProduct.name}
        </h1>

        {/* Product hero image */}
        <div className="relative w-full aspect-[16/10] rounded-3xl overflow-hidden mb-6 bg-gradient-to-br from-slate-800/60 to-slate-900/80 border border-white/5">
          <div className="absolute inset-0 flex items-center justify-center">
            {/* Yogurt bowl placeholder */}
            <div className="relative w-40 h-28">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-200 to-slate-100 rounded-full shadow-xl" />
              <div className="absolute inset-2 bg-gradient-to-br from-white to-slate-100 rounded-full" />
              {/* Swirl pattern */}
              <div className="absolute inset-4 rounded-full border-2 border-slate-200/50" />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-slate-200 rounded-full" />
            </div>
            {/* Blueberries */}
            <div className="absolute bottom-6 left-8 flex gap-1">
              <div className="w-3 h-3 bg-indigo-900 rounded-full" />
              <div className="w-2.5 h-2.5 bg-indigo-800 rounded-full" />
              <div className="w-3 h-3 bg-indigo-900 rounded-full" />
            </div>
          </div>
        </div>

        {/* Quick Take card */}
        <div className="glass-card p-5 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-foreground">Quick Take (sample)</h2>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {mockProduct.quickTake}
          </p>
        </div>

        {/* Ingredients card */}
        <div className="glass-card p-5 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <List className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-foreground">Ingredients</h2>
          </div>
          <div className="flex flex-col gap-3">
            {mockProduct.ingredients.map((ingredient) => (
              <div
                key={ingredient.name}
                className="flex items-center justify-between py-2 border-b border-white/5 last:border-0"
              >
                <span className="text-sm text-foreground">{ingredient.name}</span>
                <div className="flex items-center gap-2">
                  {ingredient.tag && (
                    <span className="text-xs text-muted-foreground px-2 py-0.5 bg-slate-800 rounded">
                      {ingredient.tag}
                    </span>
                  )}
                  <Check className="w-4 h-4 text-violet-400" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Allergens card */}
        <div className="rounded-3xl p-5 mb-4 bg-slate-900/80 backdrop-blur-xl border border-coral-red/20">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <h2 className="text-lg font-semibold text-foreground">Allergens</h2>
          </div>
          <div className="flex flex-wrap gap-2 mb-3">
            {mockProduct.allergens.contains.map((allergen) => (
              <span
                key={allergen}
                className="px-3 py-1 text-xs font-medium text-red-400 bg-red-500/15 border border-red-500/30 rounded-full"
              >
                Contains {allergen}
              </span>
            ))}
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {mockProduct.allergens.warning}
          </p>
        </div>

        {/* Nutrition Notes card */}
        <div className="glass-card p-5 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-foreground">Nutrition Notes</h2>
          </div>
          <div className="flex flex-col gap-4">
            {mockProduct.nutritionNotes.map((note) => (
              <div key={note.title} className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-violet-500/15 flex items-center justify-center">
                  {note.icon === "protein" ? (
                    <Activity className="w-4 h-4 text-violet-400" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-violet-400" />
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">{note.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {note.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Better questions to ask */}
        <div className="mb-6">
          <h3 className="mono-label text-muted-foreground mb-3">Better questions to ask</h3>
          <div className="flex flex-col gap-2">
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="flex cursor-not-allowed items-center gap-2 rounded-full border border-white/8 bg-slate-800/60 px-4 py-3 text-left opacity-50 touch-target"
            >
              <FlaskConical className="w-4 h-4 text-violet-400" />
              <span className="text-sm text-foreground">
                Show probiotic strains (preview)
              </span>
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="flex cursor-not-allowed items-center gap-2 rounded-full border border-white/8 bg-slate-800/60 px-4 py-3 text-left opacity-50 touch-target"
            >
              <GitCompareArrows className="w-4 h-4 text-violet-400" />
              <span className="text-sm text-foreground">
                Compare with regular yogurt (preview)
              </span>
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="flex cursor-not-allowed items-center gap-2 rounded-full border border-white/8 bg-slate-800/60 px-4 py-3 text-left opacity-50 touch-target"
            >
              <Leaf className="w-4 h-4 text-violet-400" />
              <span className="text-sm text-foreground">
                Sustainability score (preview)
              </span>
            </button>
          </div>
        </div>

        {/* Divider */}
        <div className="w-full h-px bg-white/5 mb-6" />

        {/* Citation */}
        <button
          type="button"
          disabled
          aria-disabled="true"
          className="mb-4 flex cursor-not-allowed items-center gap-2 text-muted-foreground opacity-50"
        >
          <Database className="w-4 h-4" />
          <span className="text-sm">Sources preview (planned citations)</span>
        </button>

        {/* Fallback card */}
        <div className="flex gap-3 p-4 rounded-2xl bg-slate-800/40 border border-white/5">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-700/60 flex items-center justify-center">
            <HelpCircle className="w-4 h-4 text-slate-400" />
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Not sure? Add a clearer photo or confirm the product details.
          </p>
        </div>
      </main>

      <BottomNav activeTab="scan" />
    </div>
  )
}
