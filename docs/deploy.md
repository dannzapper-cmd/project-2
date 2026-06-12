# SnapInsight deploy readiness

Block 19A hardens the deployed SnapInsight path for Vercel Production, Vercel
Preview, and Render. Gemini Live remains implemented but disabled by default
until the deployment owner explicitly activates it.

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

Default backend CORS allows local frontend origins:

- `http://localhost:3000`
- `http://127.0.0.1:3000`

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
| `SNAPINSIGHT_ALLOWED_ORIGINS` | Comma-separated exact frontend origins for CORS. Include the canonical production frontend URL. |
| `SNAPINSIGHT_ALLOWED_ORIGIN_REGEX` | Optional scoped regex for Vercel Preview origins owned by this project/team. |
| `SNAPINSIGHT_CACHE_ENABLED` | Defaults to `true`. |
| `SNAPINSIGHT_CACHE_TTL_SECONDS` | Defaults to `900`. |
| `SNAPINSIGHT_CACHE_MAX_ENTRIES` | Defaults to `50`. |
| `SNAPINSIGHT_MAX_IMAGE_MB` | Defaults to `8`. |
| `SNAPINSIGHT_MAX_ANALYSES_PER_SESSION` | Defaults to `5`; per-client session via `X-SnapInsight-Session-Id`. |
| `SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION` | Defaults to `10`. |
| `SNAPINSIGHT_MAX_COMPARE_PER_SESSION` | Defaults to `3`. |
| `SNAPINSIGHT_DAILY_ANALYSIS_LIMIT` | Defaults to `100`; process-local UTC day counter. |
| `SNAPINSIGHT_DAILY_COST_LIMIT_USD` | Defaults to `5`; conservative estimated Gemini spend guardrail. |
| `SNAPINSIGHT_GRAPH_ENABLED` | Defaults to `true`; set `false` to skip Neo4j sync attempts. |
| `NEO4J_URI` | Optional Neo4j Aura URI for graph persistence of public product metadata. |
| `NEO4J_USERNAME` | Required with `NEO4J_URI` for Neo4j sync. |
| `NEO4J_PASSWORD` | Required with `NEO4J_URI` for Neo4j sync. Keep server-side only. |
| `SNAPINSIGHT_LLMOPS_ENABLED` | Optional; set `true` to enable Langfuse backend tracing. |
| `LANGFUSE_PUBLIC_KEY` | Required when LLMOps tracing is enabled. Keep server-side only. |
| `LANGFUSE_SECRET_KEY` | Required when LLMOps tracing is enabled. Keep server-side only. |
| `LANGFUSE_BASE_URL` | Required when LLMOps tracing is enabled. |
| `LANGFUSE_TRACING_ENVIRONMENT` | Optional safe environment label for traces/health/metrics. |
| `SNAPINSIGHT_GEMINI_LIVE_ENABLED` | Defaults to `false`; set `true` only when activating Gemini Live. |
| `SNAPINSIGHT_GEMINI_LIVE_MODEL` | Optional; defaults to `gemini-3.1-flash-live-preview`. |
| `SNAPINSIGHT_LIVE_ACCESS_CODE` | Optional but strongly recommended/expected before Live activation. Keep server-side only. |
| `SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS` | Defaults to `120`. |
| `SNAPINSIGHT_LIVE_MAX_FRAMES_PER_SECOND` | Defaults to `1`. |
| `SNAPINSIGHT_LIVE_AUDIO_ENABLED` | Defaults to `true`. |
| `SNAPINSIGHT_LIVE_VISION_ENABLED` | Defaults to `true`. |
| `SNAPINSIGHT_LIVE_SYSTEM_INSTRUCTION` | Optional server-side system instruction locked into ephemeral token constraints. |
| `PORT` | Usually injected by the backend host. |

CORS behavior:

- Exact origins from `SNAPINSIGHT_ALLOWED_ORIGINS` remain the primary allowlist.
- The backend never defaults to `*`, and wildcard `*` is ignored.
- Vercel Preview deployments produce changing URLs, so use
  `SNAPINSIGHT_ALLOWED_ORIGIN_REGEX` for a safe owner-scoped preview pattern.
- Do not use an ownerless wildcard that allows every `vercel.app` deployment.

Production example:

```bash
SNAPINSIGHT_ANALYSIS_MODE=gemini
GEMINI_API_KEY=<server-side-only>
GEMINI_MODEL=gemini-2.5-flash
SNAPINSIGHT_ALLOW_MOCK_FALLBACK=false
SNAPINSIGHT_CACHE_ENABLED=true
SNAPINSIGHT_CACHE_TTL_SECONDS=900
SNAPINSIGHT_CACHE_MAX_ENTRIES=50
SNAPINSIGHT_MAX_IMAGE_MB=8
SNAPINSIGHT_MAX_ANALYSES_PER_SESSION=5
SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION=10
SNAPINSIGHT_MAX_COMPARE_PER_SESSION=3
SNAPINSIGHT_DAILY_ANALYSIS_LIMIT=100
SNAPINSIGHT_DAILY_COST_LIMIT_USD=5
SNAPINSIGHT_ALLOWED_ORIGINS=https://your-frontend.example
```

Preview regex example for this project/owner:

```bash
SNAPINSIGHT_ALLOWED_ORIGIN_REGEX=^https://project-2-[a-z0-9-]+-dannzapper-1603s-projects\.vercel\.app$
```

Keep the regex in Render env/config, not in source code. If the Vercel team or
project slug changes, update the regex and redeploy Render.

Do not hardcode production domains in source.

## Frontend deploy target

Deploy the Next.js app to Vercel or a Vercel-compatible host from the repository
root.

Required frontend environment variable:

| Variable | Notes |
| --- | --- |
| `NEXT_PUBLIC_SNAPINSIGHT_API_URL` | HTTPS backend base URL, for example `https://your-api.example`. Set it for Vercel Production, Preview, and Development when those builds should call the deployed backend. |

Do not put `GEMINI_API_KEY`, `LANGFUSE_SECRET_KEY`,
`SNAPINSIGHT_LIVE_ACCESS_CODE`, Neo4j credentials, private keys, access tokens,
or other secrets in Vercel `NEXT_PUBLIC_*` variables. Public frontend env values
are bundled into browser code.

After changing `NEXT_PUBLIC_SNAPINSIGHT_API_URL`, redeploy Vercel. Existing
Vercel builds do not pick up changed public env vars until rebuilt.

## Smoke checks after deploy

Automated checks that do not require secrets:

```bash
BACKEND_BASE_URL=https://your-api.example \
FRONTEND_URL=https://your-frontend.example \
python3 scripts/smoke_check.py
```

The script checks:

- frontend URL reachability when `FRONTEND_URL` is set
- `GET /health`
- `GET /v1/metrics/summary`
- `GET /v1/live/config`
- mock chat only when the backend is in mock mode
- compare and graph with synthetic analysis JSON
- optional CORS preflight using `PREVIEW_ORIGIN` or `FRONTEND_URL`
- safe health/metrics/Live config responses with no secret field names

It skips image analysis because deployed analysis can call Gemini and
OpenFoodFacts; run that manually with the checklist in `docs/smoke-test.md`.

Render free instances can cold-start. The smoke script retries transient network
or 5xx failures a few times so a waking backend does not look like a broken app.

To verify a Vercel Preview deployment:

```bash
BACKEND_BASE_URL=https://your-api.example \
PREVIEW_ORIGIN=https://your-preview.vercel.app \
python3 scripts/smoke_check.py
```

If CORS is configured correctly, the preflight check should report the preview
origin as allowed.

Manual backend liveness URLs:

- `https://your-api.example/health`
- `https://your-api.example/v1/metrics/summary`
- `https://your-api.example/v1/live/config`

After changing `SNAPINSIGHT_ALLOWED_ORIGINS` or
`SNAPINSIGHT_ALLOWED_ORIGIN_REGEX`, redeploy Render so the middleware receives
the new settings.

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
- Gemini Live status is exposed as safe booleans/model metadata only. Health and
  metrics do not call Google live. See [`gemini-live.md`](./gemini-live.md).

## Demo URL strategy

- Use the stable Vercel Production frontend URL for demos.
- Treat random Vercel Preview URLs as PR validation targets, not canonical demo
  links.
- Use one canonical Render backend URL in `NEXT_PUBLIC_SNAPINSIGHT_API_URL`.
- Confirm `/health`, `/v1/metrics/summary`, and `/v1/live/config` before a demo.
- The safe default demo can run in `mock` mode without Gemini quota. Real Gemini
  demos require `SNAPINSIGHT_ANALYSIS_MODE=gemini` and a server-side
  `GEMINI_API_KEY`.
- Gemini Live disabled state is expected until activation and should not block
  upload/analyze, chat, compare, graph, or Langfuse validation.

## Gemini Live activation

Gemini Live is disabled by default even though the code path is implemented.
Activation when the owner is ready:

1. Set `SNAPINSIGHT_GEMINI_LIVE_ENABLED=true` in Render.
2. Ensure `GEMINI_API_KEY` is present in Render.
3. Set `SNAPINSIGHT_LIVE_ACCESS_CODE` in Render.
4. Redeploy Render.
5. Redeploy Vercel only if frontend public env changed.
6. Do not add `GEMINI_API_KEY` or access codes to Vercel `NEXT_PUBLIC_*` env vars.
7. Open the app, start Live from the Scan screen, and confirm safe Langfuse
   telemetry.

The process-local Live token guardrail is effective for a single Render process.
Multi-instance deployments would need a shared limiter; no DB or Redis is added
for Block 18E.

## Known limitations

- In-memory cache, metrics, and usage limits reset on backend restart.
- Cache, metrics, and usage limits are not shared across workers or instances.
- No auth, database, Redis, or persistent storage.
- No uploaded images are stored by SnapInsight.
- Gemini API key is required for real analysis.
- OpenFoodFacts availability and community data completeness may vary.
- Visual polish, accessibility review, and larger product UX cleanup are deferred
  to Block 19B/future work.
