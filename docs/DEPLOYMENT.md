# Deployment guide

SnapInsight deploys as a **mobile-first PWA** (Vercel) + **FastAPI API** (Render). This is the portfolio close-out deployment reference.

Related: [ENV_VARS.md](./ENV_VARS.md) · [smoke-test.md](./smoke-test.md) · [troubleshooting.md](./troubleshooting.md) · [deploy.md](./deploy.md) (extended Block 19A notes)

---

## Backend — Render

### Service setup

- **Root directory:** `backend/`
- **Runtime:** Python 3.11+
- **Start command:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

- **Health check path:** `/health` (expect `status: "ok"`)

### Required env vars (production demo)

Set in Render → Environment (see [ENV_VARS.md](./ENV_VARS.md)):

- `SNAPINSIGHT_ANALYSIS_MODE=gemini`
- `GEMINI_API_KEY` (secret)
- `GEMINI_MODEL=gemini-2.5-flash`
- `SNAPINSIGHT_ALLOW_MOCK_FALLBACK=false`
- `SNAPINSIGHT_ALLOWED_ORIGINS` = your Vercel production URL
- Usage/cost guardrails (`SNAPINSIGHT_MAX_*`, `SNAPINSIGHT_DAILY_*`)
- Cache knobs (`SNAPINSIGHT_CACHE_*`, `SNAPINSIGHT_MAX_IMAGE_MB`)

### CORS

- Exact production origin in `SNAPINSIGHT_ALLOWED_ORIGINS`
- Optional `SNAPINSIGHT_ALLOWED_ORIGIN_REGEX` for scoped Vercel Preview URLs
- Backend never defaults to `*`; wildcard entries are ignored

### After env changes

Redeploy Render so middleware and settings reload.

---

## Frontend — Vercel

### Project setup

- Deploy from repository **root** (Next.js app)
- **Required env:** `NEXT_PUBLIC_SNAPINSIGHT_API_URL` = Render backend HTTPS URL
- Set for **Production**, **Preview**, and **Development** as needed

### After env changes

Trigger a **new Vercel deployment** — existing builds do not pick up changed public env vars.

### Secrets

Do **not** add `GEMINI_API_KEY` or other backend secrets to Vercel.

---

## Smoke test

```bash
BACKEND_BASE_URL=https://your-api.onrender.com \
FRONTEND_URL=https://your-frontend.vercel.app \
python3 scripts/smoke_check.py
```

Vercel Preview CORS check:

```bash
BACKEND_BASE_URL=https://your-api.onrender.com \
PREVIEW_ORIGIN=https://your-preview.vercel.app \
python3 scripts/smoke_check.py
```

The script checks:

| Check | Notes |
|-------|-------|
| Frontend reachable | When `FRONTEND_URL` set |
| `GET /health` | Mode, Gemini configured boolean |
| `GET /v1/metrics/summary` | Counters + usage limit fields |
| `GET /v1/live/config` | Expect `enabled: false` in close-out |
| Chat (mock only) | When backend `analysis_mode=mock` |
| Compare / graph | Synthetic payloads |
| CORS preflight | When `PREVIEW_ORIGIN` or `FRONTEND_URL` set |

`POST /v1/analyze/image` is **manual** (may call Gemini + Open Food Facts). See [smoke-test.md](./smoke-test.md).

Render free tier may cold-start; the script retries transient 5xx/network errors.

---

## Confirm Gemini real is active

1. `GET /health` → `analysis_mode: "gemini"`, `gemini_configured: true`
2. Upload a product image in the PWA → response `mode: "gemini"`
3. `GET /v1/metrics/summary` → `counters.gemini_requests` increases on non-cached analyses

---

## Known deployment limitations

- Cache, metrics, and usage limits are **in-memory** per process — reset on restart, not shared across instances
- No auth on `/v1/metrics/summary` (demo observability only)
- Gemini Live code exists but is **disabled** for this close-out (`SNAPINSIGHT_GEMINI_LIVE_ENABLED=false`)
