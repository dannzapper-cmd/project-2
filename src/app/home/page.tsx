"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ScanLine, Upload, FlaskConical, Lock, CheckCircle, Layers } from "lucide-react";
import { Header } from "@/components/header";
import { BottomNav } from "@/components/bottom-nav";
import { statusChips } from "@/lib/mock-data";

const iconMap = {
  lock: Lock,
  check: CheckCircle,
  layers: Layers,
};

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-20">
      <Header />

      <main className="flex-1 px-5 py-6">
        {/* Main Scan Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-3xl p-6 text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-violet-500/20 flex items-center justify-center">
            <ScanLine className="w-8 h-8 text-violet-400" />
          </div>
          
          <h2 className="text-2xl font-bold text-foreground mb-2">Analyze a product</h2>
          <p className="text-muted-foreground text-sm mb-6 text-balance">
            Ready to explore. Point your camera at a label to begin.
          </p>
          
          <Link
            href="/scan"
            className="flex items-center justify-center gap-2 h-12 gradient-btn rounded-full text-white font-medium text-sm transition-transform active:scale-[0.98] mx-auto max-w-[200px] w-full"
          >
            <ScanLine className="w-4 h-4" />
            Scan Now
          </Link>
        </motion.div>

        {/* Action Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 gap-3 mt-4"
        >
          <button
            type="button"
            className="glass-card rounded-2xl p-4 flex flex-col items-center gap-2 min-h-[88px] transition-all hover:bg-white/5 active:scale-[0.98]"
          >
            <Upload className="w-6 h-6 text-muted-foreground" />
            <span className="mono-label text-muted-foreground">Upload Image</span>
          </button>
          
          <Link
            href="/result"
            className="glass-card rounded-2xl p-4 flex flex-col items-center gap-2 min-h-[88px] transition-all hover:bg-white/5 active:scale-[0.98]"
          >
            <FlaskConical className="w-6 h-6 text-muted-foreground" />
            <span className="mono-label text-muted-foreground">Try Sample</span>
          </Link>
        </motion.div>

        {/* Status Chips */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-wrap justify-center gap-2 mt-8"
        >
          {statusChips.map((chip) => {
            const Icon = iconMap[chip.icon as keyof typeof iconMap];
            return (
              <div
                key={chip.label}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/5"
              >
                <Icon className="w-3.5 h-3.5 text-violet-400" />
                <span className="mono-label text-muted-foreground">{chip.label}</span>
              </div>
            );
          })}
        </motion.div>
      </main>

      <BottomNav />
    </div>
  );
}
