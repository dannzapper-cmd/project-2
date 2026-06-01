# SnapInsight — Portfolio Pitch

Concise narrative for hiring managers and technical interviewers. Claims map to this repository and deployed configuration patterns—not hypothetical features.

---

## 60-second pitch

SnapInsight is a mobile-first PWA I built and deployed for **product intelligence**: you photograph a packaged item, get structured analysis grounded in Open Food Facts when there’s a match, then chat, compare, or explore a lightweight product graph. It’s a full stack—Next.js on Vercel, FastAPI on Render—with explicit **mock, Gemini, and mock-fallback modes** so demos stay honest and cheap, optional Langfuse tracing that logs operational metadata only, and Gemini Live fully implemented but turned off until I choose to activate it. It’s designed as a real product workflow with citations and confidence—not a single API call dressed up as an app.

---

## 2-minute technical pitch

**Problem:** Barcode apps miss damaged or unknown codes; generic vision chat doesn’t cite sources or support a compare workflow.

**What I shipped:** A camera-first PWA with a versioned FastAPI backend. Analysis routes through a router that supports `mock` for CI and demos, `gemini` for real multimodal JSON, and opt-in `mock_fallback` that’s visibly labeled and excluded from cache. Open Food Facts grounding adds citations and enrichment; compare and chat reuse the current product context without persisting user history. GraphRAG Lite syncs public product metadata to Neo4j when configured, with an in-memory fallback. Caching stores response objects keyed by a SHA256 digest of image bytes—never the image itself.

**Operations:** Each analysis can emit a Langfuse trace with `analysis_mode`, `cache_hit`, `grounding_status`, `citations_count`, `warnings_count`, `graph_backend`, `fallback_used`, `latency_ms`, and `error_type`—no image bytes, prompts, or keys. Block 19A hardened CORS for Vercel Preview regex, smoke checks, and troubleshooting docs. Gemini Live uses backend-minted ephemeral tokens and a browser-to-Gemini WebSocket so Render doesn’t proxy audio.

**What I’d probe in an interview:** How I’d add shared rate limiting, perceptual cache keys, and production metrics without breaking the privacy model.

---

## Why I built this

I wanted to show I can ship a **consumer-shaped AI product** end to end: multimodal input, grounded outputs, degradation paths, and deployment—not just a notebook or a chat wrapper. Food/CPG was a practical vertical because Open Food Facts is open and citable, which forces good UX habits around uncertainty and attribution.

---

## What makes it technically defensible

| Layer | Evidence in repo |
|-------|------------------|
| **Grounding** | OFF match pipeline, citations, enrichment—not raw LLM prose only |
| **Reliability** | `mock` / `gemini` / `mock_fallback`; fallback not cached |
| **Router** | `analysis_router.py` mode selection and metrics |
| **Observability** | Langfuse allowlist; `/v1/metrics/summary`; safe health fields |
| **Cost controls** | Mock default, cache TTL/max entries, Live disabled + caps |
| **Deployment** | Vercel + Render docs, smoke script, CORS regex, Block 19A audit |
| **Graph** | Neo4j optional with fallback—scope controlled |
| **Live architecture** | Ephemeral tokens, no media persistence on backend |

This is closer to a **small product platform** than a tutorial API call.

---

## What I would do differently

1. **Earlier shared API contract tests** between frontend and FastAPI would have reduced integration churn across blocks.
2. **I’d narrow initial graph scope**—GraphRAG Lite is useful for demos but Neo4j ops are heavy for MVP; in-memory graph alone might have shipped first.
3. **I’d instrument session-level metrics earlier** (compare completion, chat follow-up) instead of leaving them as framework-only docs.
4. **Perceptual caching**—I used exact-byte SHA256 keys for safety; near-duplicate photos don’t hit cache, which costs more at scale.

---

## Differentiation line

**It’s a cited, mode-aware product intelligence pipeline with production deployment and observability—not a wrapper around `generateContent`.**

Use that when asked why this project vs. a generic CS degree capstone.

---

## Related docs

- [case-study.md](./case-study.md)
- [README.md](../README.md)
- [demo-guide.md](./demo-guide.md)
