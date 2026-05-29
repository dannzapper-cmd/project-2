"use client"

import { ScanLine, Lightbulb, GitCompareArrows, Activity } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

interface BottomNavProps {
  activeTab?: "scan" | "insights" | "compare" | "activity"
  className?: string
}

const navItems = [
  { id: "scan" as const, label: "Scan", icon: ScanLine, href: "/home" },
  { id: "insights" as const, label: "Insights", icon: Lightbulb, href: "/insights" },
  { id: "compare" as const, label: "Compare", icon: GitCompareArrows, href: "/compare" },
  { id: "activity" as const, label: "Activity", icon: Activity, href: "/activity" },
]

export function BottomNav({ activeTab = "scan", className }: BottomNavProps) {
  return (
    <nav
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-t border-white/5 safe-area-bottom",
        className
      )}
    >
      <div className="flex items-center justify-around px-4 py-2">
        {navItems.map((item) => {
          const isActive = activeTab === item.id
          const Icon = item.icon
          
          return (
            <Link
              key={item.id}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-1 py-2 px-4 rounded-2xl transition-all touch-target",
                isActive
                  ? "text-violet-500"
                  : "text-slate-400 hover:text-slate-300"
              )}
            >
              <div
                className={cn(
                  "flex items-center justify-center w-12 h-8 rounded-2xl transition-colors",
                  isActive && "bg-violet-500/15"
                )}
              >
                <Icon
                  className={cn(
                    "w-5 h-5 transition-colors",
                    isActive ? "text-violet-500" : "text-slate-400"
                  )}
                />
              </div>
              <span
                className={cn(
                  "text-xs font-medium transition-colors",
                  isActive ? "text-violet-500" : "text-slate-400"
                )}
              >
                {item.label}
              </span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
