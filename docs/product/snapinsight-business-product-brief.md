# SnapInsight — Business & Product Research Brief

**Status:** Source of truth for Block 20A product packaging. Market figures below come from this research brief and external sources cited within it; validate before commercial use.

**Date:** May 31, 2026  
**Purpose:** Foundations for README, business case, metrics, case study, demo guide, limitations, cost/privacy, scaling narrative, mobile packaging, and positioning.

---

## Executive summary

SnapInsight is a mobile-first Progressive Web App (PWA) for product intelligence. Users capture or upload product images; the system applies multimodal AI analysis, grounds outputs in [Open Food Facts](https://world.openfoodfacts.org/) with explicit citations, and supports structured insights, contextual chat, side-by-side comparison, GraphRAG Lite, and optional Langfuse observability.

**Current stack:** Next.js PWA + FastAPI + Neo4j Aura GraphRAG Lite (with in-memory fallback) + Gemini (feature-flagged) + intentional `mock` / `mock_fallback` modes.

**Deployment:** Production-hardened on Vercel (frontend) and Render (backend), with cost and privacy controls. Gemini Live is implemented but disabled by environment until controlled activation.

---

## Market context (research brief — validate before commercial use)

| Topic | Research brief figure | Notes |
|-------|----------------------|--------|
| Global CPG market | ~USD 3.45T (2025) → ~USD 4.23T by 2030 (4.2% CAGR) | Industry reports cited in full brief |
| E-commerce returns | ~15–20% average; ~14% attributed to inaccurate/incomplete descriptions | Operational friction driver |
| Multimodal AI shopping assistants | ~USD 4.26–4.62B (2025); high projected CAGRs | Growing category |
| Open Food Facts scale | >4.5M products; large public API traffic | Grounding foundation |

---

## Product definition

**Tagline:** AI Visual Companion for Products.

Camera-first discovery for packaged foods and CPG: vision, grounded retrieval, chat, compare, and observability—not a generic chatbot or barcode-only scanner.

---

## Target users

| Persona | Primary jobs-to-be-done |
|---------|-------------------------|
| Everyday consumer / shopper | Understand labels and compare options quickly |
| Health-conscious shopper | Transparent, cited data (not medical advice) |
| Retail / e-commerce operator | Faster product Q&A and catalog context |
| D2C product manager | Competitive benchmarking and claim context |
| Customer support / product QA | Auditable, grounded answers with traceability |
| Small business / reseller | Low-cost on-demand product intelligence |

---

## Business value (conservative)

SnapInsight **can help** with:

- Faster product understanding vs. manual label reading or scattered web search
- Grounded, cited product data where Open Food Facts matches exist
- Side-by-side comparison for purchase or QA decisions
- Support/QA knowledge assistance with observable modes and fallbacks
- Reduced manual product research in covered categories

Value is highest where Open Food Facts coverage is strong. This is **not** guaranteed ROI or medical guidance.

---

## Metrics framework (definitions only)

See [docs/business-metrics.md](../business-metrics.md) for full definitions. Metrics include: time saved per lookup, information completeness, citation/grounding coverage, fallback rate, cache hit rate, cost per analysis, latency p50/p95, compare completion, chat follow-up, support deflection potential, user trust indicators, discovery speed, and manual research reduction.

**No production results are claimed here** until instrumented and measured.

---

## Monetization paths (future — beyond current MVP)

1. B2C freemium scanner (accounts, limits, payments)
2. B2B product intelligence dashboard (teams, export, auth)
3. API for product enrichment (usage billing, SLAs)
4. Internal QA/support tool (SSO, audit logs)
5. White-label product advisor (embed, theming)
6. Affiliate/commerce assistant (ethical transparency required)

All paths need additional product, auth, and commercial infrastructure.

---

## Differentiation

- Product-specific workflow (capture → analyze → cite → chat → compare → graph)
- Open Food Facts grounding with explicit citations
- Compare mode and contextual chat scoped to current product
- GraphRAG Lite (Neo4j Aura + fallback)
- Langfuse-safe aggregate tracing (no raw media/prompts)
- Privacy/cost controls and three-mode analysis architecture (`mock` / `gemini` / `mock_fallback`)
- PWA-first deployment with deployment hardening (Blocks 19A+)
- Gemini Live feature-flagged (disabled-safe by default)

---

## App packaging path

- **Now:** PWA is sufficient for demos and early users.
- **Likely first store path:** Android Trusted Web Activity (TWA) / Bubblewrap.
- **Later:** Capacitor for iOS/Android native wrappers.
- Store distribution is **optional** and not required for technical credibility.

See [docs/mobile-packaging.md](../mobile-packaging.md).

---

## Limitations (summary)

- Open Food Facts is community-contributed and incomplete in some categories.
- AI can misidentify products; image quality matters.
- Not medical advice; not a guaranteed recommendation engine.
- Gemini Live implemented but not activated in default production config.
- Mock modes exist for safe demos and cost control.
- No native app store listing yet; no accounts/payments/enterprise auth.

See [docs/limitations.md](../limitations.md).

---

## Scaling roadmap (summary)

1. Current PWA/API product (deployed, smoke-tested)
2. Controlled Gemini activation
3. Expanded product matching and data coverage
4. Optional saved comparisons/history (privacy-first)
5. Android TWA/Bubblewrap packaging
6. Capacitor iOS/Android
7. B2B dashboard/API
8. Stronger evals, rate limiting, Sentry, always-on backend
9. Additional verticals beyond CPG

See [docs/scaling-roadmap.md](../scaling-roadmap.md).

---

## Related documentation

| Document | Purpose |
|----------|---------|
| [business-case.md](../business-case.md) | Market, personas, monetization, competition |
| [business-metrics.md](../business-metrics.md) | Metric definitions and measurement plan |
| [case-study.md](../case-study.md) | Technical narrative and decisions |
| [product-positioning.md](../product-positioning.md) | Positioning and messaging guardrails |
| [portfolio-pitch.md](../portfolio-pitch.md) | Hiring/portfolio pitch |
