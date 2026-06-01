# SnapInsight smoke test guide

Block 14/15 smoke checks are basic deploy validation, not final QA.

## Automated smoke script

Run against a local or deployed backend:

```bash
BACKEND_BASE_URL=http://127.0.0.1:8000 python3 scripts/smoke_check.py
```

Optional frontend check:

```bash
BACKEND_BASE_URL=https://your-api.example \
FRONTEND_URL=https://your-frontend.example \
python3 scripts/smoke_check.py
```

Optional Vercel Preview CORS check:

```bash
BACKEND_BASE_URL=https://your-api.example \
PREVIEW_ORIGIN=https://your-preview.vercel.app \
python3 scripts/smoke_check.py
```

The script runs without Gemini keys, real images, or live OpenFoodFacts calls:

- `GET /health`
- `GET /v1/metrics/summary`
- `GET /v1/live/config`
- `POST /v1/chat/product` only when backend analysis mode is `mock`
- `POST /v1/compare/products` with synthetic analysis payloads
- `POST /v1/graph/product` with synthetic analysis payload
- CORS preflight when `PREVIEW_ORIGIN` or `FRONTEND_URL` is set

`POST /v1/analyze/image` is skipped by the script because real deployed analysis
may call Gemini and OpenFoodFacts. If image analysis needs verification, use the
manual checklist below.

The script retries transient network or 5xx failures to reduce false negatives
from Render cold starts. It does not require real Gemini or Gemini Live to be
enabled.

## Manual post-deploy checklist

- [ ] Frontend deployed
- [ ] Backend deployed
- [ ] Frontend env points to backend URL
- [ ] Vercel `NEXT_PUBLIC_SNAPINSIGHT_API_URL` is set for Production and Preview
- [ ] Backend CORS exact origins allow the production frontend URL
- [ ] Backend CORS regex allows the scoped Vercel Preview URL pattern
- [ ] Backend `GEMINI_API_KEY` configured if running real Gemini mode
- [ ] `/health` works on deployed backend
- [ ] `/v1/metrics/summary` works
- [ ] `/v1/live/config` returns `enabled=false` and `status=disabled` when Live is off
- [ ] Image analysis works in the intended mode (`mock`, `gemini`, or visible `mock_fallback`)
- [ ] OpenFoodFacts barcode grounding works
- [ ] `no_match` product remains graceful
- [ ] Chat works with citations
- [ ] Voice Lite works or degrades gracefully
- [ ] Compare works with two products
- [ ] Cache hit/miss observable
- [ ] No image/audio/chat/compare persistence
- [ ] No medical or absolute health claims

## Privacy and safety checks

- Do not paste secrets into requests, screenshots, or logs.
- Do not upload sensitive images during smoke testing.
- Confirm uploaded images are not written to disk or persistent storage.
- Confirm audio remains browser-only and is not sent to the backend.
- Confirm chat and compare payloads are not persisted server-side.
- Confirm health, metrics, and Live config expose status booleans only, not
  secrets, access codes, tokens, media, prompts, transcripts, or raw payloads.
