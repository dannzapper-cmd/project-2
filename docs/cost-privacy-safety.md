# SnapInsight — Cost, Privacy, and Safety

**Status:** Implemented controls in production paths, plus planned hardening for scale. This document describes what the deployed system does today and what remains future work.

---

## Analysis modes and API cost control

| Control | Behavior |
|---------|----------|
| `SNAPINSIGHT_ANALYSIS_MODE=mock` | No Gemini spend. Default for safe demos and CI. |
| `SNAPINSIGHT_ANALYSIS_MODE=gemini` | Real multimodal calls; requires server-side `GEMINI_API_KEY`. |
| `SNAPINSIGHT_ALLOW_MOCK_FALLBACK` | When `true`, failed Gemini can return visible `mock_fallback`; fallback responses are **not cached**. |
| Gemini Live disabled by default | `SNAPINSIGHT_GEMINI_LIVE_ENABLED=false` blocks token minting until owner activation. |
| Live session caps | `SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS`, frame rate limits, optional access code. |
| Session usage caps | `SNAPINSIGHT_MAX_ANALYSES_PER_SESSION`, `SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION`, `SNAPINSIGHT_MAX_COMPARE_PER_SESSION` via `X-SnapInsight-Session-Id`. |
| Daily usage caps | `SNAPINSIGHT_DAILY_ANALYSIS_LIMIT` and `SNAPINSIGHT_DAILY_COST_LIMIT_USD` (process-local, UTC day). |

**Demo guidance:** Prefer `mock` for routine low-cost walkthroughs. Use `gemini` only when demonstrating real model behavior with owner approval.

---

## Usage limits (in-memory guardrails)

Session limits are keyed by the browser `X-SnapInsight-Session-Id` header (set automatically by the PWA). Daily limits are global per backend process.

| Variable | Default | Notes |
|----------|---------|-------|
| `SNAPINSIGHT_MAX_ANALYSES_PER_SESSION` | `5` | Includes cache hits. |
| `SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION` | `10` | Per session. |
| `SNAPINSIGHT_MAX_COMPARE_PER_SESSION` | `3` | Per session. |
| `SNAPINSIGHT_DAILY_ANALYSIS_LIMIT` | `100` | Resets at UTC midnight; not shared across instances. |
| `SNAPINSIGHT_DAILY_COST_LIMIT_USD` | `5` | Conservative **estimated** Gemini spend only (not billing). |

When a limit is reached, the API returns HTTP `429` with a user-facing `message` (no crash). Counters appear in `/v1/metrics/summary` as `usage_limits_*` fields.

### Confirm real Gemini is active

1. `GET /health` → `analysis_mode: "gemini"` and `gemini_configured: true`.
2. Upload a product image → response `mode: "gemini"` (not `mock` or `mock_fallback`).
3. `/v1/metrics/summary` → `counters.gemini_requests` increases on non-cached analyses.

### Test limits locally

```bash
cd backend
SNAPINSIGHT_ANALYSIS_MODE=mock \
SNAPINSIGHT_MAX_ANALYSES_PER_SESSION=2 \
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Send three `POST /v1/analyze/image` requests with the same `X-SnapInsight-Session-Id` header; the third should return `429` / `session_analysis_limit`.

---

## Caching (cost and latency)

- In-memory LRU cache stores **successful analysis response objects only**—never raw image bytes.
- Cache keys use a **SHA256 digest** of image bytes + analysis mode + model version + key version (one-way; bytes are not recoverable from the key).
- **Fallback results are not cached** so a transient outage cannot pin mock output for the full TTL.
- Cache is process-local: resets on restart; not shared across Render instances.
- Tunables: `SNAPINSIGHT_CACHE_ENABLED`, `SNAPINSIGHT_CACHE_TTL_SECONDS`, `SNAPINSIGHT_CACHE_MAX_ENTRIES`.

Perceptual/near-duplicate caching remains a future optimization (see [scaling-roadmap.md](./scaling-roadmap.md)).

---

## What is sent where

| Data | Destination | Stored by SnapInsight? |
|------|-------------|------------------------|
| Product image (upload/capture) | Backend for analysis; Gemini when in `gemini` mode | **No** persistent image storage |
| Open Food Facts lookups | Public OFF API from backend | **No** raw OFF payload persistence |
| Chat questions | Backend orchestration (Gemini when enabled) | **No** server-side chat history DB |
| Voice Lite audio | Browser speech APIs only | **Not sent** to SnapInsight backend |
| Gemini Live A/V (when enabled) | Browser ↔ Gemini WebSocket | **No** media persistence on SnapInsight |
| Langfuse metadata | Langfuse (optional) | Aggregate fields only (see below) |

---

## What is **not** stored or logged

- Raw uploaded images, audio, or video files on disk or database
- Base64 blobs in application logs
- Raw prompts, full chat transcripts, or user questions in Langfuse
- Open Food Facts raw JSON in traces
- API keys, access codes, ephemeral Live tokens, or authorization headers in traces
- PII or personal product notes

Client-side EXIF stripping/resizing runs before upload where supported (falls back to original file on failure).

---

## Langfuse (optional, safe metadata only)

When `SNAPINSIGHT_LLMOPS_ENABLED=true` and Langfuse credentials are configured, each analysis request can produce a Langfuse trace containing:

`analysis_mode` (`gemini` / `mock` / `mock_fallback`), `cache_hit` (boolean), `grounding_status`, `citations_count`, `warnings_count`, `graph_backend`, `fallback_used`, `latency_ms`, and `error_type` if applicable.

Chat, compare, graph, and Live lifecycle events emit similarly bounded metadata. **No image bytes, base64, raw prompts, transcripts, API keys, or PII** are logged.

Tracing is **optional and non-blocking**—the app functions normally if Langfuse is disabled or misconfigured.

See [llmops.md](./llmops.md).

---

## Gemini Live privacy model

- Backend mints **short-lived ephemeral tokens** with server-side `GEMINI_API_KEY`; browser never receives the API key.
- Optional `SNAPINSIGHT_LIVE_ACCESS_CODE` required before token issuance when set.
- Microphone, camera frames, and Live text go **directly to Gemini**, not through Render proxying.
- SnapInsight receives only **aggregate lifecycle telemetry** (duration, frame counts, status)—not transcripts or media.

Default production: Live **disabled**. See [gemini-live.md](./gemini-live.md).

---

## Safety boundaries

| Rule | Implementation |
|------|----------------|
| No medical diagnosis | Prompts, copy, and UX disclaimers |
| No absolute health claims | Informational framing; verify on package |
| No counterfeit claims | Blocked by product scope |
| Cite data sources | Open Food Facts attribution and source cards |
| Show uncertainty | Confidence UI, modes, warnings, fallback labels |
| User judgment | User must confirm identification and allergen decisions |

Allergen and nutrition fields are presented as **sourced from datasets or model interpretation**, with explicit “check the package” messaging.

---

## Secrets and configuration

- All API keys (`GEMINI_API_KEY`, Langfuse, Neo4j, Live access code) are **server-side only**.
- Never commit secrets; use Render/Vercel secret stores.
- Never place secrets in `NEXT_PUBLIC_*` frontend variables.

---

## Open Food Facts attribution

UI and docs reference Open Food Facts under its open database terms. Product URLs and IDs are cited when matches exist. Community data quality limitations are documented in [limitations.md](./limitations.md).

---

## Provider cost verification

Do not publish hard cost guarantees. Verify current quotas and pricing on official pages before scaling:

- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Open Food Facts](https://world.openfoodfacts.org/data)
- [Vercel pricing](https://vercel.com/pricing)
- [Render pricing](https://render.com/pricing)
- [Langfuse pricing](https://langfuse.com/pricing)
- [Neo4j Aura](https://neo4j.com/pricing/)

---

## Related docs

- [limitations.md](./limitations.md)
- [deploy.md](./deploy.md)
- [demo-guide.md](./demo-guide.md)
- [llmops.md](./llmops.md)
