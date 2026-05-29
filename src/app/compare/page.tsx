"use client";

import { motion } from "framer-motion";
import { GitCompare } from "lucide-react";
import { Header } from "@/components/header";
import { BottomNav } from "@/components/bottom-nav";

export default function ComparePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background pb-20">
      <Header />

      <main className="flex-1 px-5 py-6 flex flex-col items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-violet-500/20 flex items-center justify-center">
            <GitCompare className="w-8 h-8 text-violet-400" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">Compare</h2>
          <p className="text-muted-foreground text-sm text-balance max-w-[280px]">
            Compare products side by side to make informed choices.
          </p>
        </motion.div>
      </main>

      <BottomNav />
    </div>
  );
}
