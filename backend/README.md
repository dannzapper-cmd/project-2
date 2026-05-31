# SnapInsight Backend

FastAPI backend for image analysis. Gemini multimodal structured output is the
canonical real analysis engine; mock mode exists for local development, tests,
CI, and controlled demo fallback.

## Current scope

- FastAPI image-analysis endpoint with mock and Gemini modes.
- Gemini calls are server-side only and required for real analysis.
- Mock fallback is opt-in and visibly labeled when enabled.
- OpenFoodFacts grounding provides the first citation foundation when a conservative match is available.
- No RAG, vector database, cache, or local product database yet.
- No database, cache, auth, storage, or deployment configuration.
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
  "mock_fallback_allowed": false
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

## Overlay and Compare Mode Lite

Overlay is a visual status layer, not object detection boxes. Compare Mode Lite uses only supplied analysis, grounding, and enrichment results; it does not call Gemini or OpenFoodFacts, store images/chat/compare history, or make medical or absolute health claims.

## Caching, privacy guardrails, and metrics

An in-memory LRU cache (no database/Redis) reduces repeated analysis latency/cost. It stores analysis responses only, keyed by a SHA-256 hash of image bytes + mode + model version; raw images and base64 are never stored, logged, or written to disk, and cache keys/hashes are never exposed in API responses or the UI. Only successful image-analysis responses (`mock`/`gemini`) are cached; chat, compare, errors, and mock fallbacks are not. Defaults: `SNAPINSIGHT_CACHE_ENABLED=true`, `SNAPINSIGHT_CACHE_TTL_SECONDS=900`, `SNAPINSIGHT_CACHE_MAX_ENTRIES=50`. Uploads over `SNAPINSIGHT_MAX_IMAGE_MB` (default 8) are rejected with HTTP 413 and a friendly message before any Gemini/OpenFoodFacts work. The client strips EXIF and resizes images via Canvas before upload where supported (HEIC excepted).

The cache and metrics are **process-local and in-memory only**: both reset on backend restart and are not shared across multiple workers/instances. They are not durable observability or persistent storage; a shared cache/metrics store (Redis/DB) is intentionally out of scope for this PR. `GET /v1/metrics/summary` exposes operational counters only — no product names, chat messages, prompts, image hashes, or user-specific data. Auth/rate limiting and deep observability/deploy QA are deferred to Block 14/15.

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
