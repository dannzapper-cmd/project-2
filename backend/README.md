# SnapInsight Backend

Minimal FastAPI backend contract for Block 3A. This service exposes a health
check and a mock image-analysis endpoint that validates an uploaded image and
returns a stable no-AI response shape for future frontend and Gemini
integration.

## Current scope

- FastAPI only.
- Deterministic mock/demo response only.
- No AI model calls.
- No Gemini integration.
- No RAG or Open Food Facts retrieval.
- No database, cache, auth, storage, or deployment configuration.
- Uploaded image bytes are read for validation and discarded; they are never
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

```bash
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
- Returns a mock/no-AI response with `mode: "mock"` and `model: "none"`.

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

`latency_ms` is measured with `time.monotonic()` for the mock request and will
vary by request.

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

For Block 3A, `content_type.startswith("image/")` is intentionally sufficient.
This value is client-declared and is not verified against file magic bytes.
Magic-byte validation is a future hardening step.
