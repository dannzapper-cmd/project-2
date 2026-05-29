# SnapInsight — Roadmap

Delivery is organized into **blocks**. Block count is not rigid: blocks may be combined only when merging does not harm quality, testability, or safety. Each implementation block should land as a focused branch and pull request when possible.

## Block 0 — Foundation / context

- Repository documentation, SPEC, architecture, limitations, cost/privacy/safety, AI workflow.
- Cursor rules and ignore patterns.
- **Status:** Current block (documentation only).

## Block 1A — Frontend foundation

- Next.js App Router scaffold at repo root (`src/`), TypeScript, Tailwind, shadcn/ui init, minimal placeholder page.
- Required before v0 screen-by-screen UI generation. No product screens yet.

## Block 1C — v0 UI integration and cleanup

- Integrated and cleaned up the v0-generated visual shell after the frontend foundation.
- Preview/mock labeling, disabled non-functional controls, preserved Neural Glass tokens, mobile-first shell with centered max-width on desktop.

## Block 1 — Premium UI / PWA shell

- Next.js app scaffold, Tailwind, shadcn/ui, mobile layout, PWA manifest and service worker shell.
- Placeholder routes; no real AI.

## Block 2 — Upload + camera snapshot

- Image picker and `getUserMedia` capture flows.
- Client validation, preview, EXIF strip (planned).

## Block 3 — FastAPI backend + API contract

- Backend project structure, health check, OpenAPI spec.
- Stub analysis endpoint returning mock structured JSON.

## Block 4 — Real multimodal AI

- Server-side Gemini (or equivalent) integration.
- Structured product analysis from image + optional user hint.

## Block 5 — Product card + confidence UX

- Insight card UI: fields, confidence meter, possible matches, “try a clearer photo.”

## Block 6 — RAG with real data / citations

- Open Food Facts ingestion or API integration.
- Source cards, attribution copy, barcode / visual match pipeline.

## Block 7 — Contextual chat

- Chat thread scoped to current product context and retrieval results.

## Block 8 — Voice interaction

- Web Speech API or equivalent for input; optional TTS for responses.

## Block 9 — Overlay + Live Vision Lite

- Lightweight visual hints; not full WebRTC live streaming in v1.

## Block 10 — Compare mode

- Two-product side-by-side comparison using same analysis pipeline.

## Block 11 — Caching + cost controls

- Perceptual hash cache, model routing, rate limits, session caps.

## Block 12 — Metrics dashboard

- In-app or linked dashboard for latency, cost, retrieval, confidence aggregates.

## Block 13 — Privacy / safety controls

- Consent copy, disclaimers, data retention policy enforcement, safety prompt suite.

## Block 14 — Evals / observability

- Langfuse (or equivalent) traces, golden-set evals, regression checks.

## Block 15 — Deploy

- Production HTTPS demo on Vercel + backend host; environment documentation.

## Block 16 — Polish

- Accessibility, performance, error states, empty states, localization hooks if needed.

## Block 17 — Product package

- README runbooks, demo script, architecture summary for operators and contributors.

## Block 18 — Optional wow features

- Export share card, shelf scan batch mode, regional dataset swap—only after core is stable.

## Sequencing notes

- **Do not skip confidence UX (Block 5)** before marketing “accurate” identification.
- **RAG (Block 6)** should follow or overlap multimodal (Block 4) only with clear stub boundaries in Block 4.
- **Voice and Live Vision** stay deferred until upload, analysis, and chat paths are reliable.
- **Deploy (Block 15)** may happen earlier for a static shell demo, but full pipeline deploy follows Blocks 4–6 minimum.

## PR guidance

- Prefer one block ≈ one branch ≈ one PR when scope allows.
- Combine blocks (e.g. 1+2) only when the PR remains reviewable and testable.
- Reference [SPEC.md](../SPEC.md) acceptance criteria in PR descriptions.
