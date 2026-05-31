# SnapInsight

**AI Visual Companion for Products** — show a product via camera or upload, get grounded multimodal analysis with citations and confidence, then chat or use voice to go deeper.

## Product vision

SnapInsight is a mobile-first progressive web app that helps people understand packaged products—starting with food and CPG—through vision, conversation, and evidence-backed insights. Unlike barcode-only scanners, SnapInsight is designed for camera-first discovery: photograph a label, package, or shelf item and receive structured analysis tied to open, citable data where available.

SnapInsight complements agentic B2B workflow tools (e.g. LeadForge) with a consumer-grade, multimodal product experience: image, voice, chat, and visual overlays—not backend-centric lead workflows.

## Initial vertical

Food, packaged goods, and consumer packaged products (CPG), grounded in open datasets such as [Open Food Facts](https://world.openfoodfacts.org/) or a curated equivalent with clear attribution.

## Planned user flow

1. **Capture** — upload an image or take a camera snapshot of a product.
2. **Analyze** — multimodal model interprets packaging, labels, and visual cues.
3. **Ground** — retrieval augments answers with product records and citations where a match exists.
4. **Present** — product card with confidence, sources, and explicit uncertainty when needed.
5. **Interact** — contextual chat and voice for follow-up questions.
6. **Measure** — operational metrics (latency, cost, retrieval quality, confidence) for reliability and iteration.

The current implementation includes the PWA shell, image upload/camera snapshot,
FastAPI analysis API, Gemini real-analysis mode, OpenFoodFacts grounding,
contextual chat, browser-only Voice Lite, Compare Mode Lite, in-memory
cache/metrics, Product Knowledge Graph / GraphRAG Lite, Live Product Session
Lite, offline tuning references, optional Langfuse LLMOps visibility, deploy
readiness docs, offline eval fixtures, and smoke checks.

## Planned stack (not implemented)

Target architecture favors API-first, cloud-first delivery: a **Next.js** PWA with **Tailwind** and **shadcn/ui**, a **FastAPI** backend, multimodal models (e.g. **Gemini Flash / Flash-Lite** or equivalent), **RAG** over Open Food Facts or curated data with citations, and observability for evals and production hygiene. Deployment targets include **Vercel** for the frontend and **Modal**, **Render**, **Railway**, **Fly**, or similar for the API. Details, alternatives, and acceptance criteria live in one place.

**See [SPEC.md](./SPEC.md) for the full stack, non-goals, and acceptance criteria.**

## Current status

**Block 18D — Focused LLMOps + DevOps visibility.** The current backend includes
optional Langfuse observability for key API flows with safe aggregate metadata
only. It adds no auth, new database, Gemini Live, fine-tuning serving, or new
uploaded-file persistence.

## Documentation

| Document | Description |
|----------|-------------|
| [SPEC.md](./SPEC.md) | Product definition, stack, non-goals, acceptance criteria |
| [docs/architecture.md](./docs/architecture.md) | Target system architecture |
| [docs/roadmap.md](./docs/roadmap.md) | Delivery blocks and sequencing |
| [docs/limitations.md](./docs/limitations.md) | Product and technical limitations |
| [docs/cost-privacy-safety.md](./docs/cost-privacy-safety.md) | Cost, privacy, and safety controls |
| [docs/ai-workflow.md](./docs/ai-workflow.md) | Development workflow across tools |
| [docs/deploy.md](./docs/deploy.md) | Deploy readiness guide and required env vars |
| [docs/smoke-test.md](./docs/smoke-test.md) | Automated and manual post-deploy smoke checks |
| [docs/llmops.md](./docs/llmops.md) | Optional Langfuse LLMOps setup, privacy guarantees, and verification |

## Limitations (summary)

SnapInsight is an informational product companion, not a medical device. It does not diagnose conditions, guarantee product identification, detect counterfeits, or promise real-time prices. Model outputs can be uncertain; confidence and fallback UX are core to the design. Images should be handled ephemerally. See [docs/limitations.md](./docs/limitations.md) for the full list.
