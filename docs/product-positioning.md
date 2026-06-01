# SnapInsight — Product Positioning

**One line:** AI Visual Companion for Products — a mobile-first, cited, multimodal workflow for understanding packaged goods.

---

## What SnapInsight is

| Dimension | Position |
|-----------|----------|
| Form factor | Mobile-first PWA (installable; Android packaging optional later) |
| Input | Camera capture or image upload (vision-first, not barcode-only) |
| Intelligence | Multimodal analysis + Open Food Facts grounding when matched |
| Follow-up | Contextual chat, compare, GraphRAG Lite |
| Operations | Optional Langfuse traces with safe metadata only |
| Deployment | Production path on Vercel + Render with smoke checks |

---

## What SnapInsight is **not**

| Misread | Clarification |
|---------|---------------|
| Medical app | **Not medical advice.** Informational product context only. |
| Generic chatbot | Chat is scoped to the **current analyzed product**, with citations—not open-ended life coaching. |
| API wrapper demo | Structured pipeline, modes, cache policy, grounding, compare, graph, and observability—not a single `generateContent` button. |
| Counterfeit detector | No authenticity claims. |
| Price comparison engine | No real-time price guarantees. |
| Guaranteed recommender | Assistive insights; user confirms identification and purchases. |

---

## Positioning pillars

### 1. Product intelligence workflow

End-to-end path: **capture → analyze → cite → chat → compare → graph**—designed for packaged products, starting with CPG/food.

### 2. Grounding and transparency

Open Food Facts citations when matches exist; visible warnings when grounding is weak or absent.

### 3. Reliability and honesty

- Three analysis modes: `mock`, `gemini`, `mock_fallback`
- Confidence and fallback UX
- Gemini Live implemented but **disabled-safe** by default

### 4. Observability without surveillance

Langfuse traces include operational fields (`analysis_mode`, `cache_hit`, `grounding_status`, `citations_count`, `warnings_count`, `graph_backend`, `fallback_used`, `latency_ms`, `error_type`)—not raw media or prompts.

### 5. Privacy and cost discipline

Ephemeral image handling; mock modes for demos; optional features behind env flags.

---

## Audiences

| Audience | Message |
|----------|---------|
| Consumers | Understand labels faster with sources—verify on package |
| Health-conscious shoppers | Cited OFF data where available—not diagnosis |
| Product / QA teams | Traceable modes and compare for internal research |
| Technical reviewers | Deployed full-stack with flags, tests, and docs |
| B2B evaluators | Foundation for enrichment API or dashboard—not yet commercial SKU |

---

## Competitive framing (honest)

SnapInsight competes on **workflow + citations + observability + safe degradation**, not on claiming highest raw vision accuracy vs. Google Lens or barcode apps.

---

## Messaging guardrails

- Use **can help**, **could support**, **potential**, **assumption** for business outcomes.
- Cite market figures only with “research brief—validate before commercial use.”
- Never claim diagnosis, guaranteed ROI, or store listing status unless true.

---

## Related docs

- [business-case.md](./business-case.md)
- [limitations.md](./limitations.md)
- [portfolio-pitch.md](./portfolio-pitch.md)
- [product/snapinsight-business-product-brief.md](./product/snapinsight-business-product-brief.md)
