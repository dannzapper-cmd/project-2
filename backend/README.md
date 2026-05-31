# SnapInsight Backend

FastAPI backend for image analysis. Gemini multimodal structured output is the
canonical real analysis engine; mock mode exists for local development, tests,
CI, and controlled demo fallback.

## Current scope

- FastAPI image-analysis endpoint with mock and Gemini modes.
- Gemini calls are server-side only and required for real analysis.
- Mock fallback is opt-in and visibly labeled when enabled.
- OpenFoodFacts grounding provides the first citation foundation when a conservative match is available.
- Contextual chat, Compare Mode Lite, Product Knowledge Graph / GraphRAG Lite,
  in-memory cache/metrics, and optional Langfuse LLMOps visibility are available.
- No auth, persistent user database, or uploaded-file storage.
- Uploaded image bytes are read for validation and analysis only; they are never
  saved to disk, database, localStorage, sessionStorage, or remote storage.

## Requirements

- Python 3.11+
- `python-multipart` is required for FastAPI multipart uploads.

## Local setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

Mock mode is the default when `SNAPINSIGHT_ANALYSIS_MODE` is unset:

```bash
SNAPINSIGHT_ANALYSIS_MODE=mock uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Gemini mode is enabled server-side with a backend environment variable:

```bash
export GEMINI_API_KEY="your-server-side-key"
export GEMINI_MODEL="gemini-2.5-flash"
export SNAPINSIGHT_ANALYSIS_MODE="gemini"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

## CORS

CORS is configured for local frontend development by default:

- `http://localhost:3000`
- `http://127.0.0.1:3000`

To override this list, set a comma-separated environment variable before
starting the server:

```bash
export SNAPINSIGHT_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
```

The backend never defaults CORS to `*`.

## Configuration

- `SNAPINSIGHT_ANALYSIS_MODE`: `mock` or `gemini`; defaults to `mock` for local development and CI.
- `GEMINI_API_KEY`: server-side key required when mode is `gemini`; never expose it as `NEXT_PUBLIC_`.
- `GEMINI_MODEL`: optional, defaults to `gemini-2.5-flash`.
- `SNAPINSIGHT_ALLOW_MOCK_FALLBACK`: `false` by default; set `true` only for controlled demo fallback.
- `SNAPINSIGHT_LLMOPS_ENABLED`: `false` by default; set `true` to enable optional Langfuse tracing.
- `LANGFUSE_PUBLIC_KEY`: required when LLMOps tracing is enabled; keep server-side only.
- `LANGFUSE_SECRET_KEY`: required when LLMOps tracing is enabled; keep server-side only.
- `LANGFUSE_BASE_URL`: required when LLMOps tracing is enabled.
- `LANGFUSE_TRACING_ENVIRONMENT`: optional safe environment label surfaced in health/metrics and traces.
- Production/demo should set `SNAPINSIGHT_ANALYSIS_MODE=gemini` and provide `GEMINI_API_KEY`.
- Missing keys or Gemini failures in gemini mode return HTTP 503 unless mock fallback is explicitly allowed.
- Gemini calls may incur provider usage costs.
- In Gemini mode, image bytes are sent to Gemini for processing but are not stored by the SnapInsight backend.

## Endpoints

### `GET /health`

Returns basic service status:

```bash
curl http://127.0.0.1:8000/health
```

Example response:

```json
{
  "status": "ok",
  "service": "snapinsight-backend",
  "mode": "mock",
  "version": "0.1.0",
  "analysis_mode": "mock",
  "gemini_configured": false,
  "mock_fallback_allowed": false,
  "cache_enabled": true,
  "llmops_enabled": false,
  "llmops_configured": false,
  "llmops_provider": "disabled",
  "llmops_environment": null
}
```

### `POST /v1/analyze/image`

Accepts `multipart/form-data` with a single image file field named `file`.

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze/image \
  -F "file=@/path/to/product-image.jpg;type=image/jpeg"
```

The endpoint:

- Requires `content_type` to start with `image/`.
- Reads the upload into memory and rejects files larger than `SNAPINSIGHT_MAX_IMAGE_MB` (default 8MB).
- Does not save or persist the image.
- Attempts OpenFoodFacts grounding after successful mock/Gemini analysis.
- Returns the stable analysis response contract.
- Uses `mode: "mock"`, `mode: "gemini"`, or `mode: "mock_fallback"`.
- Returns `grounding_status` and OpenFoodFacts citations when available.

Example response shape:

```json
{
  "request_id": "generated-uuid",
  "mode": "mock",
  "status": "completed",
  "product": {
    "display_name": "Product image received",
    "category": "unknown",
    "brand": null,
    "detected_attributes": [
      "Image accepted",
      "Ready for future multimodal analysis"
    ],
    "confidence": {
      "score": 0.0,
      "label": "mock"
    }
  },
  "insights": [
    {
      "title": "Analysis not connected yet",
      "body": "This response is a mock contract for the future multimodal pipeline.",
      "type": "system"
    }
  ],
  "warnings": [
    "Mock/demo response only; no AI model was called.",
    "No image was stored."
  ],
  "citations": [],
  "next_questions": [
    "What product is this?",
    "What would you like to know about it?"
  ],
  "privacy": {
    "image_stored": false,
    "image_retention": "none"
  },
  "meta": {
    "model": "none",
    "latency_ms": 3,
    "api_version": "v1"
  }
}
```

`latency_ms` is measured with `time.monotonic()` and will vary by request.

## OpenFoodFacts grounding

OpenFoodFacts is the first citation and product-enrichment source for SnapInsight. It is community-contributed, so nutrition, label, and additive data are supplementary and may be incomplete. Barcode matches produce high enrichment confidence; name-based matches produce medium confidence. SnapInsight does not provide medical diagnosis or absolute health claims from OpenFoodFacts data. No uploaded images or OpenFoodFacts responses are stored, and no database, cache, or vector DB is added in this block.

## Contextual chat and Voice Lite

Product chat uses the current analysis result, grounding, citations, and enrichment context only; no image bytes or raw OpenFoodFacts payloads are sent. Chat is stateless and not stored server-side. Voice Lite is browser-only speech recognition/synthesis; no audio is sent to the backend. Medical diagnosis, absolute health claims, Gemini Live, server-side voice, and persistent memory are deferred.

## Product Knowledge Graph (Block 18A)

`POST /v1/graph/product` accepts a completed `AnalyzeImageResponse` and returns an
ephemeral evidence graph (nodes, edges, GraphRAG Lite paths). The graph is built
from the current analysis only — never from a hardcoded example. When
`SNAPINSIGHT_GRAPH_ENABLED=true` and Neo4j Aura env vars are set, public product
metadata may be synced to Neo4j; otherwise the backend uses in-memory fallback
without failing the request. Graph nodes never include image bytes, audio,
prompts, secrets, session IDs, or other user-identifying data. Product chat
context is enriched with compact graph evidence paths when available.

## Overlay and Compare Mode Lite

Overlay is a visual status layer, not object detection boxes. Compare Mode Lite uses only supplied analysis, grounding, and enrichment results; it does not call Gemini or OpenFoodFacts, store images/chat/compare history, or make medical or absolute health claims.

## Caching, privacy guardrails, and metrics

An in-memory LRU cache (no database/Redis) reduces repeated analysis latency/cost. It stores analysis responses only, keyed by a SHA-256 hash of image bytes + mode + model version; raw images and base64 are never stored, logged, or written to disk, and cache keys/hashes are never exposed in API responses or the UI. Only successful image-analysis responses (`mock`/`gemini`) are cached; chat, compare, errors, and mock fallbacks are not. Defaults: `SNAPINSIGHT_CACHE_ENABLED=true`, `SNAPINSIGHT_CACHE_TTL_SECONDS=900`, `SNAPINSIGHT_CACHE_MAX_ENTRIES=50`. Uploads over `SNAPINSIGHT_MAX_IMAGE_MB` (default 8) are rejected with HTTP 413 and a friendly message before any Gemini/OpenFoodFacts work. The client strips EXIF and resizes images via Canvas before upload where supported (HEIC excepted).

The cache and metrics are **process-local and in-memory only**: both reset on backend restart and are not shared across multiple workers/instances. They are not durable observability or persistent storage; a shared cache/metrics store (Redis/DB) is intentionally out of scope for this PR. `GET /v1/metrics/summary` exposes operational counters only — no product names, chat messages, prompts, image hashes, or user-specific data. Auth/rate limiting and final QA remain out of scope for Block 14/15 deploy readiness.

## Optional Langfuse LLMOps (Block 18D)

Langfuse tracing is optional and backend-only. The backend initializes one
process-local Langfuse client when `SNAPINSIGHT_LLMOPS_ENABLED=true` and
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL` are all
present. Missing env vars, SDK import errors, client errors, or Langfuse outages
degrade to no-op and must not affect API responses.

Traced flows use aggregate metadata only:

- analysis mode, latency, cache hit/miss, grounding status, citation count,
  warning count, fallback status, and high-level error type;
- chat message count, question length, context presence, citation/warning counts,
  latency, and status;
- compare diff/citation/warning counts, latency, and status;
- graph backend and graph count metadata.

The backend never sends image/audio bytes, base64, filenames, EXIF, raw prompts,
raw user questions, full chat contents, full compare payloads, raw
OpenFoodFacts payloads, secrets, API keys, authorization headers, or PII to
Langfuse. `/health` and `/v1/metrics/summary` expose only safe precomputed
LLMOps fields and never call Langfuse live. See
[`../docs/llmops.md`](../docs/llmops.md) for setup, privacy details, and the
Render/Langfuse verification checklist.

## Deploy readiness, evals, and smoke checks

See [`../docs/deploy.md`](../docs/deploy.md) and
[`../docs/smoke-test.md`](../docs/smoke-test.md).

Useful local validation commands from the repository root:

```bash
python3 -m compileall -q backend/app
python3 -m pytest backend/tests -v
python3 backend/evals/run_evals.py
python3 scripts/smoke_check.py
npm run lint
npm run build
```

The eval script is offline fixture validation only: it does not call Gemini,
OpenFoodFacts, backend services, or upload/store images. The smoke script checks
health, metrics, mock chat when the backend is in mock mode, and compare with
synthetic analysis JSON. Real Gemini image analysis and OpenFoodFacts matching
remain manual post-deploy checks.

## Validation examples

Reject a non-image upload:

```bash
printf "not an image" > /tmp/not-image.txt
curl -X POST http://127.0.0.1:8000/v1/analyze/image \
  -F "file=@/tmp/not-image.txt;type=text/plain"
```

Expected result: `400` with a clear unsupported file type message.

Reject an oversized image-declared upload:

```bash
python3 - <<'PY'
from pathlib import Path
Path("/tmp/oversized-image.bin").write_bytes(b"0" * (10 * 1024 * 1024 + 1))
PY

curl -X POST http://127.0.0.1:8000/v1/analyze/image \
  -F "file=@/tmp/oversized-image.bin;type=image/png"
```

Expected result: `413` with a file-too-large message.

## MIME validation limitation

For the current backend blocks, `content_type.startswith("image/")` is intentionally sufficient.
This value is client-declared and is not verified against file magic bytes.
Magic-byte validation is a future hardening step.
