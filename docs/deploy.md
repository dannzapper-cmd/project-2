# SnapInsight deploy readiness

Block 14/15 prepares SnapInsight for live deployment and basic operational
validation. It is not final QA, final polish, or a production-domain deploy.

## Local development

Frontend:

```bash
npm install
npm run dev
```

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
SNAPINSIGHT_ANALYSIS_MODE=mock uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Set `NEXT_PUBLIC_SNAPINSIGHT_API_URL=http://127.0.0.1:8000` for local frontend
API calls.

## Backend deploy target

Use a Render/Railway-compatible FastAPI service from the `backend/` directory.
Production start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Required backend environment variables:

| Variable | Notes |
| --- | --- |
| `SNAPINSIGHT_ANALYSIS_MODE` | Use `gemini` for real deployed analysis; `mock` for dev/CI only. |
| `GEMINI_API_KEY` | Required when analysis mode is `gemini`; keep server-side only. |
| `GEMINI_MODEL` | Optional; defaults to `gemini-2.5-flash`. |
| `SNAPINSIGHT_ALLOW_MOCK_FALLBACK` | Defaults to `false`; only enable for controlled demos. |
| `SNAPINSIGHT_ALLOWED_ORIGINS` | Comma-separated frontend origins for CORS. |
| `SNAPINSIGHT_CACHE_ENABLED` | Defaults to `true`. |
| `SNAPINSIGHT_CACHE_TTL_SECONDS` | Defaults to `900`. |
| `SNAPINSIGHT_CACHE_MAX_ENTRIES` | Defaults to `50`. |
| `SNAPINSIGHT_MAX_IMAGE_MB` | Defaults to `8`. |
| `SNAPINSIGHT_GRAPH_ENABLED` | Defaults to `true`; set `false` to skip Neo4j sync attempts. |
| `NEO4J_URI` | Optional Neo4j Aura URI for graph persistence of public product metadata. |
| `NEO4J_USERNAME` | Required with `NEO4J_URI` for Neo4j sync. |
| `NEO4J_PASSWORD` | Required with `NEO4J_URI` for Neo4j sync. Keep server-side only. |
| `SNAPINSIGHT_LLMOPS_ENABLED` | Optional; set `true` to enable Langfuse backend tracing. |
| `LANGFUSE_PUBLIC_KEY` | Required when LLMOps tracing is enabled. Keep server-side only. |
| `LANGFUSE_SECRET_KEY` | Required when LLMOps tracing is enabled. Keep server-side only. |
| `LANGFUSE_BASE_URL` | Required when LLMOps tracing is enabled. |
| `LANGFUSE_TRACING_ENVIRONMENT` | Optional safe environment label for traces/health/metrics. |
| `PORT` | Usually injected by the backend host. |

CORS behavior: when `SNAPINSIGHT_ALLOWED_ORIGINS` is not set, the backend allows
only `http://localhost:3000`. It never defaults to `*`. In deployment, set:

```bash
SNAPINSIGHT_ALLOWED_ORIGINS=https://your-frontend.example
```

Do not hardcode production domains in source.

## Frontend deploy target

Deploy the Next.js app to Vercel or a Vercel-compatible host from the repository
root.

Required frontend environment variable:

| Variable | Notes |
| --- | --- |
| `NEXT_PUBLIC_SNAPINSIGHT_API_URL` | HTTPS backend base URL, for example `https://your-api.example`. |

## Smoke checks after deploy

Automated checks that do not require secrets:

```bash
BACKEND_BASE_URL=https://your-api.example \
FRONTEND_URL=https://your-frontend.example \
python3 scripts/smoke_check.py
```

The script checks `/health`, `/v1/metrics/summary`, mock chat only when the
backend is in mock mode, and compare with synthetic analysis JSON. It skips image
analysis because deployed analysis can call Gemini and OpenFoodFacts; run that
manually with the checklist in `docs/smoke-test.md`.

## Observability notes

- Existing responses/errors include `request_id` where implemented for analysis,
  chat, and compare. This PR documents that behavior but does not extend endpoint
  schemas or service code for request IDs.
- `/health` exposes non-secret readiness signals: mode, version, Gemini key
  presence as a boolean, mock fallback status, cache status, and safe LLMOps
  status fields.
- `/v1/metrics/summary` exposes operational counters and safe LLMOps status only.
  It does not expose product names, prompts, chat messages, image hashes, or
  user-specific data.
- Optional Langfuse tracing covers analysis, chat, compare, and graph flows with
  aggregate metadata only. Health and metrics do not call Langfuse live, and
  Langfuse outages must never fail Render health checks. See
  [`llmops.md`](./llmops.md).

## Known limitations

- In-memory cache and metrics reset on backend restart.
- Cache and metrics are not shared across workers or instances.
- No auth, database, Redis, or persistent storage.
- No uploaded images are stored by SnapInsight.
- Gemini API key is required for real analysis.
- OpenFoodFacts availability and community data completeness may vary.
- Final QA, accessibility polish, and production hardening are later work.
