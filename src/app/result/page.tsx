"use client";

import { motion } from "framer-motion";
import {
  Sparkles,
  ListChecks,
  AlertTriangle,
  TrendingUp,
  CheckCircle,
  FlaskConical,
  Database,
  HelpCircle,
  ChevronRight,
} from "lucide-react";
import { Header } from "@/components/header";
import { BottomNav } from "@/components/bottom-nav";
import { mockProduct } from "@/lib/mock-data";

export default function ResultPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-24">
      <Header showBack backHref="/home" />

      <main className="flex-1 px-5 py-4 overflow-y-auto">
        {/* Confidence Badge */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-3"
        >
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-violet-500/20 rounded-full border border-violet-500/30">
            <CheckCircle className="w-3.5 h-3.5 text-violet-400" />
            <span className="mono-label text-violet-300">{mockProduct.confidence}</span>
          </div>
        </motion.div>

        {/* Product Title */}
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="text-2xl font-bold text-foreground mb-4"
        >
          {mockProduct.name}
        </motion.h1>

        {/* Product Image */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card rounded-3xl overflow-hidden mb-4 aspect-[4/3] flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900"
        >
          <div className="relative">
            {/* Bowl */}
            <div className="w-48 h-28 bg-gradient-to-b from-slate-200 to-slate-300 rounded-[50%] relative overflow-hidden shadow-xl">
              {/* Yogurt */}
              <div className="absolute inset-2 bg-gradient-to-br from-gray-50 to-gray-100 rounded-[50%]">
                {/* Swirl */}
                <div className="absolute inset-4 flex items-center justify-center">
                  <div className="w-8 h-8 border-4 border-gray-200 rounded-full border-t-transparent animate-pulse" />
                </div>
              </div>
            </div>
            {/* Spoon */}
            <div className="absolute -right-8 bottom-0 w-4 h-20 bg-gradient-to-b from-slate-300 to-slate-400 rounded-full transform rotate-45" />
            {/* Blueberries */}
            <div className="absolute -left-4 top-4 w-3 h-3 bg-indigo-900 rounded-full shadow-sm" />
            <div className="absolute -left-6 top-8 w-2.5 h-2.5 bg-indigo-800 rounded-full shadow-sm" />
            <div className="absolute -left-2 top-10 w-2 h-2 bg-indigo-900 rounded-full shadow-sm" />
          </div>
        </motion.div>

        {/* Quick Take */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="glass-card rounded-2xl p-4 mb-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-foreground">Quick Take</h2>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {mockProduct.quickTake}
          </p>
        </motion.div>

        {/* Ingredients */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card rounded-2xl p-4 mb-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <ListChecks className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-foreground">Ingredients</h2>
          </div>
          <div className="space-y-3">
            {mockProduct.ingredients.map((ingredient) => (
              <div key={ingredient.name} className="flex items-center justify-between">
                <span className="text-sm text-foreground">{ingredient.name}</span>
                <div className="flex items-center gap-2">
                  {ingredient.tag && (
                    <span className="mono-label text-xs text-muted-foreground px-2 py-0.5 bg-white/5 rounded-full">
                      {ingredient.tag}
                    </span>
                  )}
                  <CheckCircle className="w-4 h-4 text-violet-400" />
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Allergens */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass-card rounded-2xl p-4 mb-4 border-l-2 border-l-destructive/50"
        >
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-destructive" />
            <h2 className="text-lg font-semibold text-foreground">Allergens</h2>
          </div>
          <div className="inline-block px-3 py-1 bg-destructive/20 rounded-full mb-3">
            <span className="text-sm font-medium text-destructive">
              {mockProduct.allergens.primary}
            </span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {mockProduct.allergens.note}
          </p>
        </motion.div>

        {/* Nutrition Notes */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-card rounded-2xl p-4 mb-6"
        >
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-foreground">Nutrition Notes</h2>
          </div>
          <div className="space-y-4">
            {mockProduct.nutritionNotes.map((note) => (
              <div key={note.title} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-violet-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <FlaskConical className="w-4 h-4 text-violet-400" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-foreground">{note.title}</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">{note.description}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Better Questions to Ask */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="mb-6"
        >
          <p className="mono-label text-muted-foreground mb-3">Better Questions to Ask</p>
          <div className="flex flex-wrap gap-2">
            {mockProduct.betterQuestions.map((question) => (
              <button
                key={question}
                type="button"
                className="flex items-center gap-1.5 px-4 py-2.5 bg-violet-500/10 rounded-full border border-violet-500/20 text-sm text-foreground hover:bg-violet-500/20 transition-colors active:scale-[0.98]"
              >
                <FlaskConical className="w-4 h-4 text-violet-400" />
                {question}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Divider */}
        <div className="h-px bg-white/5 mb-4" />

        {/* Citation */}
        <motion.button
          type="button"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex items-center gap-2 text-muted-foreground mb-4 hover:text-foreground transition-colors"
        >
          <Database className="w-4 h-4" />
          <span className="text-sm">Open product data source</span>
          <ChevronRight className="w-4 h-4 ml-auto" />
        </motion.button>

        {/* Fallback Card */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="glass-card rounded-2xl p-4 flex items-start gap-3"
        >
          <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center flex-shrink-0">
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          <p className="text-sm text-muted-foreground">
            Not sure? Add a clearer photo or confirm the product details.
          </p>
        </motion.div>
      </main>

      <BottomNav />
    </div>
  );
}
