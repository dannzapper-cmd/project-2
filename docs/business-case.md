# SnapInsight — Business Case

**Status:** Product and market framing for reviewers and stakeholders. Conservative language throughout; market figures from the [research brief](./product/snapinsight-business-product-brief.md) should be validated before commercial use.

---

## Target market and problem

### Market context (research brief — validate before commercial use)

- **CPG** is a very large global category (research brief cites ~USD 3.45T in 2025).
- **E-commerce returns** remain elevated (industry averages ~15–20%; research brief cites ~14% linked to inaccurate or incomplete product descriptions).
- **Multimodal AI shopping assistants** are a growing segment (research brief cites market size in the low billions USD with high projected growth).
- **Open Food Facts** provides open product data at scale (>4.5M products per research brief) useful for grounding—not perfect coverage.

### Problems SnapInsight can help address

| Problem | How SnapInsight could support (not guarantee) |
|---------|-----------------------------------------------|
| Incomplete product descriptions (online/offline) | Faster structured read of packaging + cited OFF data |
| Label overload at point of purchase | Visual analysis + chat follow-up on one product |
| Manual support/QA research | Grounded answers with observable modes and traces |
| Generic visual search without citations | Product workflow with explicit sources and compare |

---

## User personas

| Persona | Jobs-to-be-done | Relevant features |
|---------|-----------------|-------------------|
| Everyday shopper | Understand a product quickly; compare options | Capture, insights, compare, chat |
| Health-conscious shopper | Transparent cited data (non-medical) | Grounding, Nutri-Score where available |
| Retail / e-commerce operator | Answer product questions faster | Analysis, chat, compare |
| D2C product manager | Benchmark competitors and claims | Compare, citations |
| Support / QA team | Consistent, traceable answers | Chat, Langfuse metadata, modes |
| Small reseller | Low-cost product intelligence | PWA, mock mode for demos |

---

## Business value (potential)

SnapInsight **can help** organizations and individuals:

- Reduce time spent on manual label reading and scattered web search (see [business-metrics.md](./business-metrics.md))
- Improve traceability via **citations** when Open Food Facts matches exist
- Support **side-by-side comparison** for purchase or internal QA decisions
- Provide **observable** analysis paths (`mock` / `gemini` / `mock_fallback`) for demos and audits

Value is **assumption-dependent** on category coverage, image quality, and whether Gemini is enabled. No guaranteed ROI is claimed.

---

## Monetization paths (future)

All paths require product and commercial build-out beyond the current MVP.

| Path | Who pays | What would need to be built |
|------|----------|----------------------------|
| B2C freemium scanner | Power users | Accounts, usage limits, payments |
| B2B product intelligence dashboard | Retail/D2C teams | Multi-user UI, export, team auth |
| Product enrichment API | Developers/brands | Public API, keys, SLAs, rate limits |
| Internal QA/support tool | Mid-size brands | SSO, audit logs, admin controls |
| White-label advisor | D2C brands | Embed SDK, theming |
| Affiliate/commerce assistant | Networks (commission) | Transparent UX; ethical guardrails |

Pricing hypotheses in the research brief (e.g. freemium tiers) are **illustrative assumptions**, not validated pricing.

---

## Competitive landscape (honest)

| Alternative | Strength | Gap vs. SnapInsight workflow |
|-------------|----------|------------------------------|
| Google Lens | Strong general visual search | Less product-specific grounding, citations, compare-on-one-session |
| General multimodal chat (ChatGPT/Gemini) | Flexible Q&A | No built-in OFF workflow, compare, or deployment-hardened product modes |
| Open Food Facts app | Excellent open data, barcode | Barcode-first; lighter vision-first + chat + observability stack |
| Nutrition/barcode scanners | Familiar UX | Varies in transparency and multimodal capture |

SnapInsight does **not** claim superior raw identification accuracy. Differentiation is the **structured, cited, observable product intelligence workflow**.

See [product-positioning.md](./product-positioning.md).

---

## Why SnapInsight is differentiated

- **Product-specific workflow:** capture → analyze → cite → chat → compare → graph
- **Open Food Facts grounding** with explicit citations
- **Three-mode analysis architecture** for cost-safe demos and visible fallback
- **Compare mode** and contextual chat scoped to current product context
- **GraphRAG Lite** (Neo4j Aura + in-memory fallback)
- **Langfuse-safe tracing** without raw media or prompts
- **Privacy/cost controls** and deployment hardening (Vercel + Render, smoke checks)
- **Gemini Live** implemented but feature-flagged off by default

---

## What would need to be built for a commercial product

| Area | Current state | Commercial gap |
|------|---------------|----------------|
| Identity & billing | None | Accounts, payments, entitlements |
| Data platform | OFF + optional Neo4j | Broader datasets, SLA, data pipeline |
| Scale & reliability | Single-process cache/metrics | Shared cache, rate limits, multi-instance Live guardrails |
| Trust & compliance | In-app disclaimers | Legal review, privacy policy, DPA |
| GTM | PWA demo | Sales materials, onboarding, support playbooks |
| Measurement | Framework defined | Production analytics, user studies |

---

## Assumptions (labeled)

- **Assumption:** Time saved per lookup is meaningful in CPG categories with strong OFF coverage.
- **Assumption:** B2B teams would pay for exportable, cited product intelligence if auth and SLAs exist.
- **Assumption:** Support deflection is possible only after integration with real support volumes (not measured yet).

---

## Related docs

- [business-metrics.md](./business-metrics.md)
- [case-study.md](./case-study.md)
- [scaling-roadmap.md](./scaling-roadmap.md)
- [product/snapinsight-business-product-brief.md](./product/snapinsight-business-product-brief.md)
