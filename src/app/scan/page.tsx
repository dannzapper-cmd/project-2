"use client";

import { motion } from "framer-motion";
import { Image as ImageIcon, Zap } from "lucide-react";
import { Header } from "@/components/header";
import { BottomNav } from "@/components/bottom-nav";
import { detectionTags } from "@/lib/mock-data";

export default function ScanPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-20">
      <Header />

      <main className="flex-1 px-5 py-4 flex flex-col">
        {/* Viewfinder Area */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="relative flex-1 max-h-[480px] rounded-3xl overflow-hidden bg-gradient-to-br from-slate-900/50 to-slate-800/30 border border-white/5"
        >
          {/* Corner brackets */}
          <div className="absolute inset-4">
            <div className="viewfinder-corner viewfinder-corner-tl" />
            <div className="viewfinder-corner viewfinder-corner-tr" />
            <div className="viewfinder-corner viewfinder-corner-bl" />
            <div className="viewfinder-corner viewfinder-corner-br" />
          </div>

          {/* Processing Status */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="absolute top-8 left-1/2 -translate-x-1/2"
          >
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/90 rounded-full border border-white/10">
              <motion.div
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 1.2, repeat: Infinity }}
                className="w-2 h-2 rounded-full bg-violet-400"
              />
              <span className="mono-label text-foreground">Processing</span>
            </div>
          </motion.div>

          {/* Detection Tags */}
          {detectionTags.map((tag, index) => (
            <motion.div
              key={tag.label}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 + index * 0.2 }}
              className="absolute"
              style={{ top: tag.position.top, left: tag.position.left, transform: "translate(-50%, -50%)" }}
            >
              <div className="px-3 py-2 bg-slate-800/90 rounded-xl border border-white/10 shadow-lg">
                <span className="text-sm text-foreground whitespace-nowrap">{tag.label}</span>
              </div>
            </motion.div>
          ))}

          {/* Scan line animation */}
          <motion.div
            animate={{ y: ["0%", "100%", "0%"] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="absolute left-4 right-4 h-0.5 bg-gradient-to-r from-transparent via-violet-400/50 to-transparent"
          />
        </motion.div>

        {/* Camera Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex items-center justify-center gap-8 py-6"
        >
          <button
            type="button"
            className="w-12 h-12 rounded-full bg-slate-800/80 border border-white/10 flex items-center justify-center transition-all hover:bg-slate-700/80 active:scale-95"
          >
            <ImageIcon className="w-5 h-5 text-muted-foreground" />
          </button>
          
          <button
            type="button"
            className="w-16 h-16 rounded-full bg-violet-400 flex items-center justify-center transition-transform active:scale-95 shadow-lg shadow-violet-500/30"
          >
            <div className="w-14 h-14 rounded-full border-4 border-violet-300/50" />
          </button>
          
          <button
            type="button"
            className="w-12 h-12 rounded-full bg-slate-800/80 border border-white/10 flex items-center justify-center transition-all hover:bg-slate-700/80 active:scale-95"
          >
            <Zap className="w-5 h-5 text-muted-foreground" />
          </button>
        </motion.div>

        {/* Privacy Note */}
        <p className="text-center text-xs text-muted-foreground">
          Images are used only for this analysis.
        </p>
      </main>

      <BottomNav />
    </div>
  );
}
