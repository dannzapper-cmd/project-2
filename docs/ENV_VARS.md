# Environment variables

Compact reference for SnapInsight deploy and local development. Server secrets stay on **Render** (backend) only. The frontend uses **one** public API URL.

See also: [DEPLOYMENT.md](./DEPLOYMENT.md) · [PRIVACY_AND_COST_CONTROLS.md](./PRIVACY_AND_COST_CONTROLS.md)

---

## Frontend (Vercel / `.env.local`)

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_SNAPINSIGHT_API_URL` | Yes (prod/preview) | HTTPS backend base URL, e.g. `https://your-api.onrender.com` |
| `NEXT_PUBLIC_SNAPINSIGHT_LIVE_ACCESS_CODE` | No | Only if backend Live is explicitly enabled (not used in project close-out) |

**Never** set `GEMINI_API_KEY`, Langfuse secrets, Neo4j credentials, or Live access codes in `NEXT_PUBLIC_*`.

Templates: [`.env.example`](../.env.example)

---

## Backend (Render / `backend/.env`)

### Analysis (Gemini real)

| Variable | Default | Notes |
|----------|---------|-------|
| `SNAPINSIGHT_ANALYSIS_MODE` | `mock` | Use `gemini` for real multimodal analysis in production |
| `GEMINI_API_KEY` | — | **Server-side only.** Required when mode is `gemini` |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Multimodal model id |
| `SNAPINSIGHT_ALLOW_MOCK_FALLBACK` | `false` | `true` = visible `mock_fallback` on Gemini failure (not cached) |

### CORS

| Variable | Notes |
|----------|-------|
| `SNAPINSIGHT_ALLOWED_ORIGINS` | Comma-separated exact frontend origins (production URL) |
| `SNAPINSIGHT_ALLOWED_ORIGIN_REGEX` | Optional scoped Vercel Preview regex |

### Cache & upload limits

| Variable | Default |
|----------|---------|
| `SNAPINSIGHT_CACHE_ENABLED` | `true` |
| `SNAPINSIGHT_CACHE_TTL_SECONDS` | `900` |
| `SNAPINSIGHT_CACHE_MAX_ENTRIES` | `50` |
| `SNAPINSIGHT_MAX_IMAGE_MB` | `8` |

### Usage / cost guardrails (in-memory)

| Variable | Default | Scope |
|----------|---------|-------|
| `SNAPINSIGHT_MAX_ANALYSES_PER_SESSION` | `5` | Per `X-SnapInsight-Session-Id` |
| `SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION` | `10` | Per session |
| `SNAPINSIGHT_MAX_COMPARE_PER_SESSION` | `3` | Per session |
| `SNAPINSIGHT_DAILY_ANALYSIS_LIMIT` | `100` | Global per backend process (UTC day) |
| `SNAPINSIGHT_DAILY_COST_LIMIT_USD` | `5` | Estimated Gemini spend guardrail (not billing) |

### Optional

| Variable | Default | Notes |
|----------|---------|-------|
| `SNAPINSIGHT_GRAPH_ENABLED` | `true` | Set `false` to skip Neo4j sync |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | — | Optional Aura graph |
| `SNAPINSIGHT_LLMOPS_ENABLED` | `false` | Langfuse tracing (non-blocking) |
| `LANGFUSE_*` | — | Required only when LLMOps enabled |
| `SNAPINSIGHT_GEMINI_LIVE_ENABLED` | `false` | **Off for project close-out** |
| `PORT` | `8000` | Injected by Render |

Templates: [`backend/.env.example`](../backend/.env.example)

---

## Production demo (Render)

```bash
SNAPINSIGHT_ANALYSIS_MODE=gemini
GEMINI_API_KEY=<server-side-only>
GEMINI_MODEL=gemini-2.5-flash
SNAPINSIGHT_ALLOW_MOCK_FALLBACK=false
SNAPINSIGHT_ALLOWED_ORIGINS=https://your-frontend.vercel.app
SNAPINSIGHT_CACHE_ENABLED=true
SNAPINSIGHT_MAX_ANALYSES_PER_SESSION=5
SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION=10
SNAPINSIGHT_MAX_COMPARE_PER_SESSION=3
SNAPINSIGHT_DAILY_ANALYSIS_LIMIT=100
SNAPINSIGHT_DAILY_COST_LIMIT_USD=5
```

## Local development (zero Gemini cost)

```bash
SNAPINSIGHT_ANALYSIS_MODE=mock
# no GEMINI_API_KEY required
```
