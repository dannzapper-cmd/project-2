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

The script runs without Gemini keys, real images, or live OpenFoodFacts calls:

- `GET /health`
- `GET /v1/metrics/summary`
- `POST /v1/chat/product` only when backend analysis mode is `mock`
- `POST /v1/compare/products` with synthetic analysis payloads

`POST /v1/analyze/image` is skipped by the script because real deployed analysis
may call Gemini and OpenFoodFacts. If image analysis needs verification, use the
manual checklist below.

`metrics/summary` may return 429 under load; this is expected behavior and the
script treats it as a non-fatal warning.

## Manual post-deploy checklist

- [ ] Frontend deployed
- [ ] Backend deployed
- [ ] Frontend env points to backend URL
- [ ] Backend CORS allows frontend URL
- [ ] Backend `GEMINI_API_KEY` configured
- [ ] `/health` works on deployed backend
- [ ] `/v1/metrics/summary` works
- [ ] Image analysis works with real Gemini
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
