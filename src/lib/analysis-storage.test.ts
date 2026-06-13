import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { AnalysisResponse } from "@/lib/snapinsight-api"
import {
  buildActivityEntry,
  getActivityLog,
  getAnalysisHistory,
  getLatestAnalysis,
  persistSuccessfulAnalysis,
} from "@/lib/analysis-storage"

function createStorage(): Storage {
  const store = new Map<string, string>()
  return {
    get length() {
      return store.size
    },
    clear() {
      store.clear()
    },
    getItem(key: string) {
      return store.get(key) ?? null
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null
    },
    removeItem(key: string) {
      store.delete(key)
    },
    setItem(key: string, value: string) {
      store.set(key, value)
    },
  }
}

function sampleAnalysis(requestId: string, name: string): AnalysisResponse {
  return {
    request_id: requestId,
    mode: "gemini",
    status: "completed",
    product: {
      display_name: name,
      category: "Snacks",
      brand: "Acme",
      detected_attributes: [],
      confidence: { score: 0.82, label: "high" },
      barcode: null,
    },
    insights: [],
    warnings: [],
    citations: [],
    next_questions: [],
    privacy: { image_stored: false, image_retention: "none" },
    meta: { model: "gemini-2.5-flash", latency_ms: 1200, api_version: "v1" },
    grounding_status: "grounded",
    grounding_summary: "Matched",
    match_method: "name_brand",
    source_product_id: "123",
    retrieved_at: null,
    source_trace: [],
    product_enrichment: null,
    cache_hit: false,
  }
}

describe("analysis-storage", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", createStorage())
    vi.stubGlobal("sessionStorage", createStorage())
    vi.stubGlobal("window", {
      dispatchEvent: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("persists latest analysis without image data", () => {
    const analysis = sampleAnalysis("req-1", "Yogurt")
    persistSuccessfulAnalysis(analysis)

    expect(getLatestAnalysis()?.product.display_name).toBe("Yogurt")
    expect(getAnalysisHistory()).toHaveLength(1)
    expect(getActivityLog()).toHaveLength(1)
  })

  it("dedupes history by request_id", () => {
    persistSuccessfulAnalysis(sampleAnalysis("req-1", "First"))
    persistSuccessfulAnalysis(sampleAnalysis("req-1", "First updated"))
    persistSuccessfulAnalysis(sampleAnalysis("req-2", "Second"))

    expect(getAnalysisHistory()).toHaveLength(2)
    expect(getAnalysisHistory()[0]?.analysis.request_id).toBe("req-2")
  })

  it("builds activity metadata without secrets", () => {
    const entry = buildActivityEntry(sampleAnalysis("req-abc", "Bar"))
    expect(entry).toMatchObject({
      product_name: "Bar",
      model: "gemini-2.5-flash",
      latency_ms: 1200,
      request_id: "req-abc",
    })
    expect(entry).not.toHaveProperty("token")
    expect(entry).not.toHaveProperty("image")
  })
})
