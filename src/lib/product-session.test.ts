import { describe, expect, it } from "vitest"

import type { AnalysisResponse } from "@/lib/snapinsight-api"
import {
  addSnapshotToSession,
  createProductSession,
  getConfidenceTrend,
  getSessionSummary,
  MAX_SESSION_SNAPSHOTS,
} from "@/lib/product-session"

function mockAnalysis(
  overrides: Partial<{
    name: string
    score: number
    grounding: AnalysisResponse["grounding_status"]
    warnings: string[]
    citations: number
    mode: AnalysisResponse["mode"]
  }> = {}
): AnalysisResponse {
  const {
    name = "Test Product",
    score = 0.5,
    grounding = "grounded",
    warnings = [],
    citations = 2,
    mode = "mock",
  } = overrides

  return {
    request_id: `req-${name}-${score}`,
    mode,
    status: "completed",
    product: {
      display_name: name,
      category: "Snacks",
      brand: "Acme",
      detected_attributes: [],
      confidence: { score, label: score >= 0.7 ? "high" : "medium" },
      barcode: null,
    },
    insights: [],
    warnings,
    citations: Array.from({ length: citations }, (_, index) => ({
      source: "OpenFoodFacts",
      title: name,
      field: `field-${index}`,
      field_label: `Field ${index}`,
      value: "value",
      url: null,
    })),
    next_questions: [],
    privacy: { image_stored: false, image_retention: "none" },
    meta: { model: "mock", latency_ms: 100, api_version: "v1" },
    grounding_status: grounding,
    grounding_summary: "summary",
    match_method: "none",
    source_product_id: null,
    retrieved_at: null,
    source_trace: [],
    product_enrichment: null,
  }
}

describe("addSnapshotToSession", () => {
  it("adds snapshots with incrementing order", () => {
    let session = createProductSession(1000)
    const first = addSnapshotToSession(session, mockAnalysis({ name: "A", score: 0.4 }), {
      nowMs: 1001,
      localKey: "a",
    })
    expect(first.added).toBe(true)
    if (!first.added) return

    session = first.session
    const second = addSnapshotToSession(session, mockAnalysis({ name: "B", score: 0.6 }), {
      nowMs: 1002,
      localKey: "b",
    })
    expect(second.added).toBe(true)
    if (!second.added) return

    expect(second.session.snapshots).toHaveLength(2)
    expect(second.session.snapshots[0].order).toBe(1)
    expect(second.session.snapshots[1].order).toBe(2)
    expect(second.session.snapshots[1].analysis.product.display_name).toBe("B")
  })

  it("returns limit_reached at max snapshots", () => {
    let session = createProductSession()
    for (let index = 0; index < MAX_SESSION_SNAPSHOTS; index += 1) {
      const result = addSnapshotToSession(
        session,
        mockAnalysis({ name: `P${index}`, score: 0.5 })
      )
      expect(result.added).toBe(true)
      if (!result.added) return
      session = result.session
    }

    const blocked = addSnapshotToSession(session, mockAnalysis({ name: "Overflow" }))
    expect(blocked.added).toBe(false)
    if (blocked.added) return
    expect(blocked.reason).toBe("limit_reached")
    expect(blocked.session.snapshots).toHaveLength(MAX_SESSION_SNAPSHOTS)
  })
})

describe("getSessionSummary", () => {
  it("returns best product by confidence and counts", () => {
    let session = createProductSession()
    for (const entry of [
      { name: "Low", score: 0.3 },
      { name: "Best", score: 0.9 },
      { name: "Mid", score: 0.6 },
    ]) {
      const result = addSnapshotToSession(
        session,
        mockAnalysis({
          name: entry.name,
          score: entry.score,
          grounding: "partial_match",
          warnings: ["warn"],
          citations: 3,
          mode: "mock_fallback",
        })
      )
      if (!result.added) return
      session = result.session
    }

    const summary = getSessionSummary(session)
    expect(summary.snapshotCount).toBe(3)
    expect(summary.bestProductName).toBe("Best")
    expect(summary.bestConfidenceScore).toBe(0.9)
    expect(summary.groundingStatusesSeen).toEqual(["partial_match"])
    expect(summary.latestWarnings).toEqual(["warn"])
    expect(summary.latestCitationCount).toBe(3)
    expect(summary.latestMode).toBe("mock_fallback")
  })

  it("returns empty summary for null session", () => {
    const summary = getSessionSummary(null)
    expect(summary.snapshotCount).toBe(0)
    expect(summary.bestProductName).toBeNull()
  })
})

describe("getConfidenceTrend", () => {
  it("returns neutral for first snapshot", () => {
    expect(getConfidenceTrend(0.8, null)).toBe("neutral")
  })

  it("returns up when score increases", () => {
    expect(getConfidenceTrend(0.7, 0.5)).toBe("up")
  })

  it("returns down when score decreases", () => {
    expect(getConfidenceTrend(0.4, 0.6)).toBe("down")
  })

  it("returns neutral when score is equal", () => {
    expect(getConfidenceTrend(0.55, 0.55)).toBe("neutral")
  })
})
