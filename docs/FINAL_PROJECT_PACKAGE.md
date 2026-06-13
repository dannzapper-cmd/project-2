# SnapInsight — Final Project Package

**Product:** AI Visual Companion for Products (food & CPG)  
**Production frontend:** https://project-2-wine-seven.vercel.app  
**Production backend health:** https://snapinsight-backend-87dm.onrender.com/health  
**Last updated:** 2026-06-13

---

## Product overview

SnapInsight is a mobile-first PWA that turns product packaging photos into structured, cited product intelligence. Users upload or capture an image, receive Gemini multimodal analysis, optional Open Food Facts grounding, contextual chat, product comparison, an evidence graph, and gated Gemini Live voice/vision — all behind session and daily cost guardrails.

## Core user flow

1. **Scan** — Upload or capture a packaged product image on `/scan`.
2. **Analyze** — Backend runs real Gemini 2.5 Flash analysis (`SNAPINSIGHT_ANALYSIS_MODE=gemini`).
3. **Ground** — Conservative Open Food Facts matching adds citations when available.
4. **Review** — Insights, warnings, nutrition enrichment, and next questions surface on scan and `/insights`.
5. **Compare** — `/compare` diffs two saved analyses (JSON only — no image bytes).
6. **Observe** — `/activity` shows local scan history plus backend metrics and usage limits.
7. **Live (optional)** — Gemini Live is access-code gated, session-limited, and experimental.

## Architecture summary

| Layer | Stack |
|-------|-------|
| Frontend | Next.js PWA on Vercel |
| Backend | FastAPI on Render |
| Vision / chat | Gemini 2.5 Flash (server-side) |
| Grounding | Open Food Facts API |
| Graph | Neo4j Aura optional; in-memory fallback |
| Observability | In-app metrics + optional Langfuse (safe metadata) |
| Persistence | Local analysis JSON only; no image storage |

See [architecture.md](./architecture.md) for diagrams and API detail.

## AI capabilities

- **Multimodal image analysis** — Product name, category, attributes, warnings, next questions.
- **Grounded enrichment** — Open Food Facts nutrition, labels, additives when matched.
- **Product-scoped chat** — Follow-ups on current analysis context.
- **Compare Mode Lite** — Structured diff from two `AnalysisResponse` objects.
- **GraphRAG Lite** — Product evidence graph (minimap removed in close-out).
- **Gemini Live** — Gated voice + vision demo (60s session, 1 FPS cap).

## Gemini real analysis

Production runs `SNAPINSIGHT_ANALYSIS_MODE=gemini` with `GEMINI_MODEL=gemini-2.5-flash`. `SNAPINSIGHT_ALLOW_MOCK_FALLBACK=false` — failures surface honestly; no silent mock substitution.

## Grounding and citations

When Open Food Facts matches (barcode or name), SnapInsight adds citations with source links and enrichment fields. Grounding status (`grounded`, `partial_match`, `no_match`, `grounding_unavailable`) is shown in UI. AI analysis remains valid when grounding is unavailable.

## Gemini Live gated mode

Live is enabled in production config but requires an access code for token issuance. Limits: **60s** max session, **1 FPS** vision frames. UI shows ready/access-gated state without exposing secrets.

## Usage and cost guardrails

| Limit | Value |
|-------|-------|
| Max analyses per session | 5 |
| Max chat messages per session | 10 |
| Max compare per session | 3 |
| Daily cost limit (USD) | 5 |

In-memory response cache (no images). Session counters via client session header.

## Privacy posture

- Images processed ephemerally; not stored server-side.
- EXIF stripped in browser where supported.
- Analysis JSON stored locally on device only.
- Compare sends analysis JSON only.
- API keys and Live access codes server-side only.

See [PRIVACY_AND_COST_CONTROLS.md](./PRIVACY_AND_COST_CONTROLS.md).

## Observability / LLMOps

- `/v1/metrics/summary` — request counters, latency, usage limit visibility.
- Optional Langfuse traces with safe metadata (no image bytes).
- Activity page surfaces backend health and Live config status.

## Evidence screenshots

Captured via `npm run evidence:screenshots`. Index: [evidence/screenshots/README.md](./evidence/screenshots/README.md).

| Screenshot | Proves |
|------------|--------|
| Mobile scan + Gemini result | Real multimodal analysis |
| Insights | Local persistence |
| Compare | JSON-only diff workflow |
| Activity | Metrics and limits |
| Graph | Evidence visualization, no minimap |
| Live panel | Gated ready state |

## Known limitations

- **Not medical advice** — Assistant for product understanding only.
- **Not a regulatory authority** — No compliance or authenticity guarantees.
- **Identification uncertainty** — Confidence scores and fallbacks required.
- **Grounding coverage** — Depends on Open Food Facts data availability.
- **Live experimental** — Gated, short sessions, browser-dependent.
- **Render cold start** — Free tier backend may take seconds to wake; banner reflects this calmly.
- **Not in app stores** — PWA / documented store path only.

## Future roadmap

- Broader product databases and retailer integrations.
- Improved barcode / GS1 Digital Link alignment ([GS1 Sunrise 2027](https://www.gs1us.org/industries-and-insights/by-topic/sunrise-2027)).
- Optional accounts and saved lists (not in current scope).
- Store packaging documented in [MOBILE_STORE_READINESS.md](./MOBILE_STORE_READINESS.md).

## Deployment links

| Resource | URL |
|----------|-----|
| Frontend | https://project-2-wine-seven.vercel.app |
| Scan | https://project-2-wine-seven.vercel.app/scan |
| Backend health | https://snapinsight-backend-87dm.onrender.com/health |
| Deploy guide | [DEPLOYMENT.md](./DEPLOYMENT.md) |
| Env reference | [ENV_VARS.md](./ENV_VARS.md) |
| Demo script | [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) |
| Business brief | [BUSINESS_BRIEF.md](./BUSINESS_BRIEF.md) |
| Screenshot guide | [SCREENSHOT_CAPTURE_GUIDE.md](./SCREENSHOT_CAPTURE_GUIDE.md) |
