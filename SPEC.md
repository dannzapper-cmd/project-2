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
| Observability | Langfuse or equivalent | Optional backend traces, latency, retrieval/fallback signals |
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

OpenFoodFacts is the first citation and product-enrichment foundation. Its nutrition, label, and additive data is community-contributed and supplementary, not guaranteed truth. Enrichment confidence follows the match method: barcode is high, name-based matching is medium. SnapInsight does not provide medical diagnosis or absolute health claims, stores no uploaded images or OpenFoodFacts responses, and adds no database, cache, vector store, or RAG pipeline in this block.

## Configuration note - Contextual chat and Voice Lite

Contextual chat uses only the current analysis, grounding, citations, and enrichment context and is not stored server-side. Voice Lite uses browser speech APIs only; no audio is sent to the backend. Medical diagnosis, absolute health claims, Gemini Live, server-side voice, and persistent memory remain out of scope.

## Configuration note — caching, privacy, and metrics

An in-memory LRU cache stores successful analysis responses only (hashed image-byte keys, never raw images/base64, keys never exposed), reducing repeated latency/cost. In-memory operational counters are exposed at `/v1/metrics/summary` for demo observability — not user analytics. Cache and metrics are process-local: both reset on backend restart and are not shared across workers, so they are not durable storage or observability. Client-side EXIF stripping/resizing runs before upload where supported and falls back to the original file on failure. No database, Redis, Sentry, auth, or persistent storage is added.

## Configuration note — optional Langfuse LLMOps

Block 18D adds optional backend Langfuse tracing controlled by
`SNAPINSIGHT_LLMOPS_ENABLED=true` plus `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`. It traces aggregate operational
metadata for analysis, chat, compare, and graph flows: modes, latency,
cache hit/miss, grounding status, citation/warning counts, graph backend,
fallback status, and high-level error type. It does not trace image/audio bytes,
base64, filenames, EXIF, raw prompts, raw user questions, full chat contents,
full compare payloads, OpenFoodFacts raw payloads, secrets, API keys,
authorization headers, or PII. Langfuse is optional: disabled, missing, or
failing configuration degrades to no-op and must not affect product responses or
health checks.

## Configuration note — Gemini Live

Block 18E implements Gemini Live as a deployment-disabled capability. The
backend mints short-lived Gemini Live ephemeral tokens with server-side
`GEMINI_API_KEY`, v1alpha auth tokens, one-use constraints, locked model,
`AUDIO` response modality, output audio transcription, and a safe server-side
system instruction. The browser uses the returned constrained WebSocket URL and
token so microphone audio, camera snapshots, and text go directly to Gemini, not
through the SnapInsight backend. SnapInsight does not persist Live media,
transcripts, raw text, tokens, or sessions. Safe telemetry is aggregate-only:
session lifecycle, duration, frame counts, text-message counts, modality flags,
status, and error type. Live remains optional and off by default via
`SNAPINSIGHT_GEMINI_LIVE_ENABLED=false`.

## Configuration note — deploy readiness, evals, and smoke harness

Block 14/15 adds deployment documentation, environment variable coverage,
offline golden-set fixture checks, and a lightweight smoke script/checklist. It
does not perform a live deploy, final QA, final polish, or add database, Redis,
auth, persistent storage, Langfuse, Sentry, user analytics, or new AI features.
Live deployment requires host-level environment variables: backend Gemini mode
and key for real analysis, frontend API URL, and backend CORS origins. Minimal
evals run offline against fixture data and must not call Gemini or
OpenFoodFacts.

Block 19A hardens the deployed configuration path: Vercel Production and Preview
builds must set `NEXT_PUBLIC_SNAPINSIGHT_API_URL`, Render CORS must use exact
production origins plus an optional owner-scoped preview regex, and smoke checks
must verify `/health`, `/v1/metrics/summary`, `/v1/live/config`, safe disabled
Gemini Live status, and optional CORS preflight without requiring real Gemini or
Gemini Live activation.

## Configuration note — Block 20A product package

Block 20A adds the final product documentation package (README, case study,
business case, metrics framework, demo guide, limitations, cost/privacy,
scaling roadmap, mobile packaging, positioning, portfolio pitch, screenshots
checklist). It links from [README.md](./README.md) and does not change runtime
behavior, activate Gemini/Gemini Live, or add media assets. See
[docs/roadmap.md](./docs/roadmap.md) Block 20A.

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
