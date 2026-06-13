import { describe, expect, it } from "vitest"

import {
  getStatusLabel,
  PENDING_BANNER_LABEL,
  WAKING_BANNER_LABEL,
} from "@/components/shared/preview-banner"
import type { HealthResponse } from "@/lib/snapinsight-api"

function baseHealth(overrides: Partial<HealthResponse> = {}): HealthResponse {
  return {
    status: "ok",
    service: "snapinsight-api",
    mode: "production",
    version: "0.1.0",
    analysis_mode: "gemini",
    gemini_configured: true,
    mock_fallback_allowed: false,
    cache_enabled: true,
    gemini_live_enabled: false,
    ...overrides,
  }
}

describe("getStatusLabel", () => {
  it("shows neutral pending copy during initial load", () => {
    expect(getStatusLabel(null, "pending")).toBe(PENDING_BANNER_LABEL)
  })

  it("shows warming copy after health failure", () => {
    expect(getStatusLabel(null, "warming")).toBe(WAKING_BANNER_LABEL)
  })

  it("reports mock mode honestly", () => {
    expect(getStatusLabel(baseHealth({ analysis_mode: "mock" }), "ready")).toBe(
      "Mock mode · Demo data"
    )
  })

  it("reports gemini mode with grounded intelligence copy", () => {
    expect(getStatusLabel(baseHealth(), "ready")).toBe(
      "Gemini mode · Grounded product intelligence"
    )
  })

  it("notes live gating when enabled", () => {
    expect(
      getStatusLabel(baseHealth({ gemini_live_enabled: true }), "ready")
    ).toBe("Gemini real analysis · Cost controlled · Live gated")
  })
})
