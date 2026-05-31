# SnapInsight — Product Specification

## Product definition

SnapInsight is a mobile-first PWA that lets users show a product to AI via image upload or camera snapshot, then receive multimodal analysis with evidence, citations, confidence indicators, and optional chat or voice follow-up. The initial domain is food and packaged CPG products, using open or curated datasets that support attribution (primarily Open Food Facts).

## Target users

- Shoppers comparing packaged foods and wanting label-level context with sources.
- Health-conscious consumers seeking informational nutrition and ingredient context (not medical advice).
- People who prefer camera-first discovery over barcode-only apps when the barcode is missing, damaged, or unknown.

## Primary demo route (planned)

`/demo` or home → capture/upload → analysis loading state → product insight card (with confidence + citations) → contextual chat panel → optional voice input.

Route names and UX are targets for Block 1+; not implemented in Block 0.

## Core capabilities (planned)

| Capability | Description | Target block |
|------------|-------------|--------------|
| Image upload | File picker with validation and preview | Block 2 |
| Camera snapshot | `getUserMedia` capture on supported devices | Block 2 |
| Live Vision Lite | Lightweight live hints (not full WebRTC streaming) | Block 9 |
| Multimodal + GenAI | Vision + text reasoning via cloud multimodal API | Block 4 |
| RAG with citations | Retrieve product records; show source cards and links | Block 6 |
| Confidence / fallback UX | Scores, possible matches, “better photo”, graceful degradation | Block 5 |
| Contextual chat | Thread grounded in current product context | Block 7 |
| Voice interaction | Speech input/output where supported | Block 8 |
| Visual overlay | Highlights on packaging regions (when feasible) | Block 9 |
| Compare mode | Side-by-side product comparison | Block 10 |
| Metrics / observability | Traces, evals, cost and quality signals | Blocks 12, 14 |

## Planned stack

| Layer | Target choice | Notes |
|-------|---------------|--------|
| Frontend | Next.js, Tailwind, shadcn/ui, PWA | Mobile-first; installable where supported |
| Backend | FastAPI (Python) | API-first contract; server-side secrets |
| Multimodal AI | Gemini 2.5 Flash-Lite primary, Flash fallback (or equivalent) | Structured JSON output; verify quotas on [official pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Data / RAG | Open Food Facts + optional curated subset | ODbL/DBCL attribution; cite in UI |
| Vector store (optional) | pgvector on Supabase or similar | Verify free-tier limits on official docs before committing |
| Observability | Langfuse or equivalent | Traces, latency, cost, retrieval quality |
| Frontend deploy | Vercel (or equivalent) | Confirm commercial terms if product goes beyond hobby use |
| Backend deploy | Modal, Render, Railway, Fly, or similar | Scale-to-zero preferred for cost control |
| Caching | Perceptual hash + response cache (future) | Reduce duplicate multimodal calls |

Stack rows are **targets**, not implemented dependencies. Verify tiers and limits against official documentation before each implementation block.

## Non-goals

- **Local fine-tuning as core** — rely on API multimodal models and RAG, not custom training pipelines.
- **Counterfeit / authenticity claims** — no “real vs fake” assertions.
- **Fragile price scraping** — no real-time price guarantees.
- **Heavy WebRTC in v1** — snapshot and upload first; live streaming deferred.
- **Full GraphRAG initially** — start with product-centric RAG; graph expansion only if core is stable.
- **Medical diagnosis** — no disease or treatment claims.
- **Absolute health claims** — informational context only; user must verify labels.
- **Unnecessary image retention** — ephemeral-by-default image handling.

## Configuration note — OpenFoodFacts grounding

OpenFoodFacts is the first citation foundation for product grounding. Its data is community-contributed and must be treated as supplementary, not guaranteed truth. SnapInsight does not provide medical diagnosis or absolute health claims from this source. Grounding does not store uploaded images or OpenFoodFacts responses, and this block does not add a database, vector store, cache, or RAG pipeline.

## Competitive positioning (informational)

Many apps excel at barcode lookup (e.g. Yuka) or generic visual search (e.g. Google Lens). SnapInsight’s planned differentiation is a **transparent, cited, confidence-aware multimodal companion** for packaged products—camera-first input, grounded retrieval, and explicit uncertainty—not a claim to outperform closed products on every dimension.

## Acceptance criteria — final product (planned)

- [ ] User can upload or capture a product image on a mobile-first PWA.
- [ ] System returns a structured product insight card with fields appropriate to food/CPG.
- [ ] When RAG matches exist, citations link to source records (e.g. Open Food Facts product URL or ID).
- [ ] Confidence and fallback UX appear when identification or retrieval is weak.
- [ ] Contextual chat respects current product context and limitations disclaimers.
- [ ] Voice interaction works on supported browsers (degraded gracefully elsewhere).
- [ ] No medical diagnosis, counterfeit, or absolute health claims in copy or model prompts.
- [ ] Images are not persisted beyond what is necessary for cache or debugging (with clear policy).
- [ ] API keys and model calls remain server-side.
- [ ] Basic observability: traces or logs for latency, cost estimates, and retrieval outcomes.
- [ ] Deployed demo accessible via HTTPS with documented setup.

## Acceptance criteria — Block 0

- [x] `README.md` describes vision, vertical, planned flow, status, and doc links without implying implementation.
- [x] `SPEC.md` is the single source of truth for stack, non-goals, and acceptance criteria.
- [x] Architecture, roadmap, limitations, cost/privacy/safety, and AI workflow docs exist under `docs/`.
- [x] `.cursor/rules/snapinsight.mdc` defines project rules with valid MDC frontmatter.
- [x] `.cursorignore` excludes high-noise paths without ignoring spec or docs.
- [x] No application runtime code, AI integration, database, auth, or deployment config added.
