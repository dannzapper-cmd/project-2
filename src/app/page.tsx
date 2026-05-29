"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ScanLine } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col bg-background">
      {/* Top Logo */}
      <div className="flex items-center gap-2 px-5 pt-6 pb-4">
        <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
          <ScanLine className="w-4 h-4 text-violet-400" />
        </div>
        <span className="text-lg font-semibold text-violet-400">SnapInsight</span>
      </div>

      {/* Hero Card */}
      <div className="flex-1 flex flex-col px-5">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="glass-card rounded-3xl overflow-hidden flex-1 max-h-[420px] relative"
        >
          {/* Phone scanning visualization */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative w-48 h-72">
              {/* Phone frame */}
              <div className="absolute inset-0 bg-slate-800 rounded-3xl border border-white/10 shadow-2xl">
                {/* Screen */}
                <div className="absolute inset-2 bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl overflow-hidden">
                  {/* Viewfinder */}
                  <div className="absolute inset-6 border-2 border-violet-500/50 rounded-xl">
                    {/* Corner brackets */}
                    <div className="viewfinder-corner viewfinder-corner-tl" />
                    <div className="viewfinder-corner viewfinder-corner-tr" />
                    <div className="viewfinder-corner viewfinder-corner-bl" />
                    <div className="viewfinder-corner viewfinder-corner-br" />
                    
                    {/* Product placeholder */}
                    <div className="absolute inset-4 flex items-center justify-center">
                      <div className="w-16 h-20 bg-gradient-to-b from-amber-700 to-amber-900 rounded-lg flex items-center justify-center">
                        <div className="text-[6px] text-amber-200 font-bold text-center leading-tight px-1">
                          ORGANIC<br />GRANOLA
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Analyzing chip */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5, duration: 0.3 }}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2"
                  >
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/90 rounded-full border border-white/10">
                      <motion.div
                        animate={{ opacity: [1, 0.5, 1] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="w-1.5 h-1.5 rounded-full bg-violet-400"
                      />
                      <span className="mono-label text-violet-300">Analyzing...</span>
                    </div>
                  </motion.div>
                </div>
              </div>
              
              {/* Hand holding phone */}
              <div className="absolute -bottom-8 -right-8 w-24 h-32 bg-gradient-to-t from-amber-800 to-amber-700 rounded-t-full opacity-60" />
            </div>
          </div>
          
          {/* Scan lines effect */}
          <motion.div
            animate={{ y: ["-100%", "100%"] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-violet-400/30 to-transparent"
          />
        </motion.div>

        {/* Headline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="mt-8 text-center"
        >
          <h1 className="text-4xl font-bold text-foreground leading-tight text-balance">
            Point. Ask.<br />Understand.
          </h1>
          <p className="mt-4 text-muted-foreground text-base leading-relaxed text-balance max-w-[300px] mx-auto">
            A visual AI companion for understanding products with evidence, confidence, and clear explanations.
          </p>
        </motion.div>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="mt-8 mb-10 flex flex-col gap-3"
        >
          <Link
            href="/scan"
            className="flex items-center justify-center gap-2 h-14 gradient-btn rounded-full text-white font-medium text-base transition-transform active:scale-[0.98]"
          >
            <ScanLine className="w-5 h-5" />
            Start scan
          </Link>
          <Link
            href="/result"
            className="flex items-center justify-center h-14 rounded-full border border-white/10 bg-white/5 text-foreground font-medium text-base transition-all hover:bg-white/10 active:scale-[0.98]"
          >
            Try sample product
          </Link>
        </motion.div>
      </div>
    </main>
  );
}
