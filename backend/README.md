# SnapInsight Backend

FastAPI backend for image analysis. The API keeps the Block 3A/3B response
contract stable while supporting mock mode and optional Gemini multimodal
analysis.

## Current scope

- FastAPI image-analysis endpoint with mock and Gemini modes.
- Gemini calls are optional and server-side only.
- Safe mock fallback when Gemini is not configured or cannot complete.
- No RAG or Open Food Facts retrieval.
- No real citations yet; `citations` remains an empty list.
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

Mock mode is the default when `GEMINI_API_KEY` is not configured:

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

## Analysis environment

- `GEMINI_API_KEY`: server-side Gemini API key. Never expose this with a
  `NEXT_PUBLIC_` prefix.
- `GEMINI_MODEL`: optional model name. Defaults to `gemini-2.5-flash`.
- `SNAPINSIGHT_ANALYSIS_MODE`:
  - `mock` forces the deterministic mock response.
  - `gemini` uses Gemini when `GEMINI_API_KEY` is present.
  - If unset, the backend uses Gemini when a key is present and mock mode when
    no key is present.

If `SNAPINSIGHT_ANALYSIS_MODE=gemini` is set without `GEMINI_API_KEY`, the API
returns a `mock_fallback` response with a safe configuration warning instead of
crashing. Gemini provider failures, timeouts, safety blocks, quota errors, or
invalid structured output also return `mock_fallback` with a user-safe warning.
Gemini calls may incur provider usage costs. Use mock mode for local UI work
when real analysis is not needed.

Privacy: in Gemini mode, image bytes are sent to Gemini for processing but are
not stored by the SnapInsight backend. The backend does not persist uploaded
images in any mode.

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
  "version": "0.1.0"
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
- Reads the upload into memory and rejects files larger than 10MB.
- Does not save or persist the image.
- Returns the stable analysis response contract.
- Uses `mode: "mock"`, `mode: "gemini"`, or `mode: "mock_fallback"`.
- Keeps `citations: []` until RAG/Open Food Facts is implemented.

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
