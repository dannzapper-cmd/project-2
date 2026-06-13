"use client"

import { useEffect, useState } from "react"

import { getHealth, type HealthResponse } from "@/lib/snapinsight-api"
import { cn } from "@/lib/utils"

interface PreviewBannerProps {
  className?: string
}

export const PENDING_BANNER_LABEL = "Warming backend · Gemini status loading"
export const WAKING_BANNER_LABEL = "Backend waking up · Try again in a few seconds"

const HEALTH_TIMEOUT_MS = 12_000
const RETRY_DELAY_MS = 2_500

export type BannerStatusState = "pending" | "warming" | "ready"

export function getStatusLabel(
  health: HealthResponse | null,
  state: BannerStatusState
): string {
  if (state === "pending") return PENDING_BANNER_LABEL
  if (state === "warming") return WAKING_BANNER_LABEL
  if (!health) return PENDING_BANNER_LABEL

  if (health.analysis_mode === "mock") return "Mock mode · Demo data"

  if (health.analysis_mode === "gemini") {
    if (health.gemini_live_enabled) {
      return "Gemini real analysis · Cost controlled · Live gated"
    }
    return "Gemini mode · Grounded product intelligence"
  }

  return `${health.analysis_mode} mode`
}

function fetchHealthWithTimeout(timeoutMs: number): Promise<HealthResponse> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

  return getHealth(controller.signal).finally(() => {
    window.clearTimeout(timeoutId)
  })
}

export function PreviewBanner({ className }: PreviewBannerProps) {
  const [label, setLabel] = useState(PENDING_BANNER_LABEL)

  useEffect(() => {
    let active = true
    let retryTimer: number | null = null

    const applyLabel = (health: HealthResponse | null, state: BannerStatusState) => {
      if (!active) return
      setLabel(getStatusLabel(health, state))
    }

    const loadHealth = async (allowRetry: boolean) => {
      try {
        const health = await fetchHealthWithTimeout(HEALTH_TIMEOUT_MS)
        applyLabel(health, "ready")
      } catch {
        if (!active) return

        if (allowRetry) {
          applyLabel(null, "pending")
          retryTimer = window.setTimeout(() => {
            void loadHealth(false)
          }, RETRY_DELAY_MS)
          return
        }

        applyLabel(null, "warming")
      }
    }

    void loadHealth(true)

    return () => {
      active = false
      if (retryTimer !== null) window.clearTimeout(retryTimer)
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
