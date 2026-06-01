# SnapInsight — Business Metrics Framework

**Status:** Definitions and measurement plan only. **No metric in this document is presented as a measured production result** unless explicitly noted. Illustrative assumptions come from the [research brief](./product/snapinsight-business-product-brief.md) and must be replaced with real data.

Each metric includes a `data_status` field:

- `not yet measured — illustrative assumption`
- `partially observable via Langfuse — needs production traffic`
- `framework defined — needs instrumentation`

---

## Summary table

| Metric | data_status |
|--------|-------------|
| Time saved per product lookup | not yet measured — illustrative assumption |
| Information completeness | framework defined — needs instrumentation |
| Citation / grounding coverage | partially observable via Langfuse — needs production traffic |
| Fallback rate | partially observable via Langfuse — needs production traffic |
| Cache hit rate | partially observable via Langfuse — needs production traffic |
| Cost per analysis | partially observable via Langfuse — needs production traffic |
| Latency p50 / p95 | partially observable via Langfuse — needs production traffic |
| Compare completion rate | framework defined — needs instrumentation |
| Chat follow-up rate | framework defined — needs instrumentation |
| Support deflection potential | not yet measured — illustrative assumption |
| User trust indicators | framework defined — needs instrumentation |
| Product discovery speed | not yet measured — illustrative assumption |
| Manual research reduction | not yet measured — illustrative assumption |

---

## Metric definitions

### Time saved per product lookup

| Field | Detail |
|-------|--------|
| **Definition** | Difference between end-to-end SnapInsight time (upload → structured insight) and a baseline manual research duration for the same intent. |
| **Why it matters** | Core productivity story for shoppers and internal teams. |
| **How to measure** | Session timing on frontend + backend `latency_ms` in traces; optional user study with timed tasks. |
| **Illustrative assumption** | Research brief model: ~15–45s vs. ~2–5 min manual search. **Not yet measured.** |
| **data_status** | not yet measured — illustrative assumption |

---

### Information completeness

| Field | Detail |
|-------|--------|
| **Definition** | Share of expected product fields (name, brand, ingredients summary, scores, allergens hints where applicable) populated in the insight card when a grounding match exists. |
| **Why it matters** | Signals whether the pipeline fills actionable structure vs. empty shells. |
| **How to measure** | Schema field presence checks on analysis JSON; stratify by OFF match method (barcode vs. name). |
| **Illustrative assumption** | Research brief suggests high completeness only for well-covered OFF categories—**category-dependent, not measured.** |
| **data_status** | framework defined — needs instrumentation |

---

### Citation / grounding coverage

| Field | Detail |
|-------|--------|
| **Definition** | Percentage of analysis sessions where at least one verifiable citation (e.g. Open Food Facts URL/ID) is attached. |
| **Why it matters** | Trust and auditability vs. pure model narration. |
| **How to measure** | Langfuse `citations_count`, `grounding_status`; backend metrics counters. |
| **Production data needed** | Sufficient traffic across categories with weak vs. strong OFF coverage. |
| **data_status** | partially observable via Langfuse — needs production traffic |

---

### Fallback rate

| Field | Detail |
|-------|--------|
| **Definition** | Share of analyses where `analysis_mode` is `mock_fallback` or explicit degradation occurred (`fallback_used=true`). |
| **Why it matters** | Cost, reliability, and honesty about live model availability. |
| **How to measure** | Langfuse `analysis_mode`, `fallback_used`; `/v1/metrics/summary` counter `mock_fallbacks`. |
| **data_status** | partially observable via Langfuse — needs production traffic |

---

### Cache hit rate

| Field | Detail |
|-------|--------|
| **Definition** | `cache_hits / (cache_hits + cache_misses)` for analysis requests when caching is enabled. |
| **Why it matters** | Direct cost and latency lever. |
| **How to measure** | Langfuse `cache_hit`; metrics summary counters. |
| **Illustrative assumption** | Research brief modeled 40–60% after ramp—**not yet measured in production.** |
| **data_status** | partially observable via Langfuse — needs production traffic |

---

### Cost per analysis

| Field | Detail |
|-------|--------|
| **Definition** | Estimated provider cost per successful `gemini` analysis (and optionally per chat/compare turn). |
| **Why it matters** | Unit economics for freemium or API pricing. |
| **How to measure** | Provider billing exports + Langfuse session counts; tag by `analysis_mode` to exclude `mock`. |
| **Illustrative assumption** | Research brief modeled sub-cent ranges with caching—**verify against current Gemini pricing.** |
| **data_status** | partially observable via Langfuse — needs production traffic |

---

### Latency p50 / p95

| Field | Detail |
|-------|--------|
| **Definition** | End-to-end server-side latency for analysis (and optionally full client-perceived time). |
| **Why it matters** | Mobile UX and demo credibility. |
| **How to measure** | Langfuse `latency_ms`; metrics latency aggregates; account for Render cold start separately. |
| **Illustrative assumption** | Research brief suggested p50 &lt;3s, p95 &lt;8s for gemini—**environment-dependent, not verified as SLA.** |
| **data_status** | partially observable via Langfuse — needs production traffic |

---

### Compare completion rate

| Field | Detail |
|-------|--------|
| **Definition** | Share of compare sessions that successfully process two products and return a diff payload without error. |
| **Why it matters** | Validates a differentiated feature, not only single-product scan. |
| **How to measure** | Compare endpoint success/failure events; frontend funnel (needs instrumentation). |
| **data_status** | framework defined — needs instrumentation |

---

### Chat follow-up rate

| Field | Detail |
|-------|--------|
| **Definition** | Share of analysis sessions followed by at least one contextual chat message. |
| **Why it matters** | Engagement signal for “companion” positioning. |
| **How to measure** | Chat trace counts per session ID (requires session correlation instrumentation). |
| **data_status** | framework defined — needs instrumentation |

---

### Support deflection potential

| Field | Detail |
|-------|--------|
| **Definition** | Estimated share of product support tickets answerable via self-serve SnapInsight flows. |
| **Why it matters** | B2B value hypothesis. |
| **How to measure** | Requires support ticket taxonomy + pilot with human review—**not available today.** |
| **Illustrative assumption** | Research brief flags as assumption until live adoption data exists. |
| **data_status** | not yet measured — illustrative assumption |

---

### User trust indicators

| Field | Detail |
|-------|--------|
| **Definition** | Composite: explicit thumbs feedback, session continuation, citation click-through, or “retake photo” rate. |
| **Why it matters** | Product quality beyond raw latency. |
| **How to measure** | UX instrumentation (mostly **not implemented**). |
| **data_status** | framework defined — needs instrumentation |

---

### Product discovery speed

| Field | Detail |
|-------|--------|
| **Definition** | Time from first capture to user-reported satisfactory identification (subjective) or successful OFF barcode match. |
| **Why it matters** | In-store and shelf-scan scenarios. |
| **How to measure** | User studies or labeled eval set—not production-instrumented yet. |
| **data_status** | not yet measured — illustrative assumption |

---

### Manual research reduction

| Field | Detail |
|-------|--------|
| **Definition** | Reduction in internal or user steps (tabs opened, minutes logged) when using SnapInsight vs. baseline workflow. |
| **Why it matters** | B2B and power-user ROI narrative (still not a guaranteed ROI). |
| **How to measure** | Task-based studies with QA/support teams. |
| **data_status** | not yet measured — illustrative assumption |

---

## Langfuse fields (canonical)

When tracing is enabled, analysis traces can include: `analysis_mode`, `cache_hit`, `grounding_status`, `citations_count`, `warnings_count`, `graph_backend`, `fallback_used`, `latency_ms`, `error_type`. No image bytes, base64, raw prompts, transcripts, API keys, or PII.

See [llmops.md](./llmops.md).

---

## Related docs

- [business-case.md](./business-case.md)
- [case-study.md](./case-study.md)
- [demo-guide.md](./demo-guide.md)
