"use client"

import { useEffect, useState } from "react"

import { getHealth, type HealthResponse } from "@/lib/snapinsight-api"
import { cn } from "@/lib/utils"

interface PreviewBannerProps {
  className?: string
}

function getStatusLabel(health: HealthResponse | null, unavailable: boolean): string {
  if (unavailable) return "Backend status unavailable"
  if (!health) return "Checking backend status…"

  if (health.analysis_mode === "mock") return "Mock mode"

  if (health.analysis_mode === "gemini") {
    if (health.gemini_live_enabled) {
      return "Gemini mode · Live gated · Cost controlled"
    }
    return "Gemini real analysis · Grounded product intelligence"
  }

  return `${health.analysis_mode} mode`
}

export function PreviewBanner({ className }: PreviewBannerProps) {
  const [label, setLabel] = useState("Checking backend status…")

  useEffect(() => {
    let active = true

    getHealth()
      .then((health) => {
        if (!active) return
        setLabel(getStatusLabel(health, false))
      })
      .catch(() => {
        if (!active) return
        setLabel(getStatusLabel(null, true))
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <div
      role="status"
      className={cn(
        "mx-5 rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-center",
        className
      )}
    >
      <span className="mono-label text-violet-400">{label}</span>
    </div>
  )
}
