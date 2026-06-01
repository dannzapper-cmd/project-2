# SnapInsight — Demo Guide

Step-by-step guide for demonstrating the **deployed** SnapInsight product. Replace placeholder URLs with your canonical Vercel Production frontend and Render backend URLs.

**Default demo posture:** `mock` analysis mode, Gemini Live **off**, Langfuse optional.

---

## URLs and endpoints

| Resource | Example | Notes |
|----------|---------|-------|
| Frontend (PWA) | `https://YOUR_FRONTEND.vercel.app` | Stable **Production** URL for demos |
| Backend base | `https://YOUR_BACKEND.onrender.com` | Set in `NEXT_PUBLIC_SNAPINSIGHT_API_URL` |
| Health | `GET /health` | Mode, cache, LLMOps flags (no secrets) |
| Metrics | `GET /v1/metrics/summary` | Operational counters |
| Live config | `GET /v1/live/config` | Must show disabled when Live off |
| Analyze | `POST /v1/analyze/image` | Multipart image upload |
| Chat | `POST /v1/chat/product` | Product-scoped chat |
| Compare | `POST /v1/compare/products` | Two analysis payloads |
| Graph | `POST /v1/graph/product` | GraphRAG Lite |
| Live token | `POST /v1/live/token` | Blocked when Live disabled |

---

## Pre-demo checklist (5 minutes)

1. Open `https://YOUR_BACKEND.onrender.com/health` — expect HTTP 200.
2. Open `https://YOUR_BACKEND.onrender.com/v1/metrics/summary` — expect JSON counters.
3. Open `https://YOUR_BACKEND.onrender.com/v1/live/config` — expect `enabled: false`, `status: "disabled"` when Live is off.
4. Open frontend — confirm no API URL errors in UI.
5. Optional: run smoke script (see below).

```bash
BACKEND_BASE_URL=https://YOUR_BACKEND.onrender.com \
FRONTEND_URL=https://YOUR_FRONTEND.vercel.app \
python3 scripts/smoke_check.py
```

Render free tier may **cold start**; retry after 30–60s if the first request fails.

---

## Verify health

```bash
curl -sS https://YOUR_BACKEND.onrender.com/health | jq .
```

Check (non-secret fields):

- `analysis_mode` — `mock` or `gemini` (your intended demo mode)
- `mock_fallback_allowed` — usually `false` unless testing fallback
- `cache_enabled`, `llmops_enabled`, `llmops_configured`

---

## Verify metrics

```bash
curl -sS https://YOUR_BACKEND.onrender.com/v1/metrics/summary | jq .
```

Use the in-app **Status / metrics** panel (if visible) for the same counters during UI demos.

Counters are **process-local** and reset on backend restart.

---

## Verify Gemini Live disabled state

```bash
curl -sS https://YOUR_BACKEND.onrender.com/v1/live/config | jq .
```

Expected when Live is off:

- `enabled` → `false`
- `status` → `"disabled"`

In the PWA Scan flow, the Live panel should show **disabled** messaging—not attempt WebSocket connection.

`POST /v1/live/token` should **not** succeed while disabled (no activation during normal low-cost demos).

---

## Analysis modes — how to explain and use

| Mode | When to use | Honest script |
|------|-------------|---------------|
| `mock` | Default low-cost demos, CI | “This is deterministic demo data—no Gemini call.” |
| `gemini` | Real multimodal demo | “This calls Gemini server-side; results vary with photo quality.” |
| `mock_fallback` | Only if env enabled | “Gemini failed; you’re seeing labeled fallback—not silent substitution.” |

### Run an image analysis (UI)

1. Open frontend → **Scan** (or home capture flow).
2. Upload a packaged food image or use camera.
3. Submit analysis.
4. Review product card: fields, confidence, citations (if OFF match), `mode` indicator.

### Run an image analysis (API)

```bash
curl -sS -X POST https://YOUR_BACKEND.onrender.com/v1/analyze/image \
  -F "file=@/path/to/product.jpg" | jq .
```

Check response `mode` and `meta.latency_ms`. Do not paste API keys or sensitive images into tickets.

---

## Test contextual chat

1. Complete an analysis in the UI.
2. Open **Chat** for the current product context.
3. Ask a follow-up (e.g. ingredients, comparison to label).
4. Confirm citations/disclaimers remain visible.

**Voice Lite:** browser speech only—audio does not hit SnapInsight backend.

---

## Test compare mode

1. Analyze product A → keep context.
2. Analyze or select product B.
3. Open **Compare** — side-by-side diff using existing analysis payloads (no duplicate OFF calls beyond design).

Verify graceful handling if one product lacks grounding.

---

## Test graph (GraphRAG Lite)

1. From a product with analysis context, open **Graph** view.
2. Confirm nodes/edges render; backend may use Neo4j or in-memory fallback (`graph_backend` in traces).

```bash
# Smoke uses synthetic JSON; manual UI test uses real analysis context.
```

---

## Verify Langfuse traces (optional)

**Prerequisites:** `SNAPINSIGHT_LLMOPS_ENABLED=true` and Langfuse keys on Render.

1. Run one analysis in `gemini` or `mock` mode.
2. Open Langfuse project → Traces.
3. Confirm fields such as: `analysis_mode`, `cache_hit`, `grounding_status`, `citations_count`, `warnings_count`, `graph_backend`, `fallback_used`, `latency_ms`.
4. Confirm **absence** of image bytes, base64, raw prompts, transcripts, API keys.

Tracing is non-blocking—disable Langfuse and confirm the app still works.

See [llmops.md](./llmops.md).

---

## What **not** to activate during normal low-cost demos

| Do not | Why |
|--------|-----|
| Set `SNAPINSIGHT_ANALYSIS_MODE=gemini` at scale | Per-image API cost |
| Enable `SNAPINSIGHT_ALLOW_MOCK_FALLBACK` without explaining it | Hides Gemini outages |
| Set `SNAPINSIGHT_GEMINI_LIVE_ENABLED=true` | Live audio/vision cost + compliance |
| Paste secrets in chat/screenshots | Security |
| Upload sensitive personal images | Privacy |

---

## Activate Gemini later (owner)

On Render:

```bash
SNAPINSIGHT_ANALYSIS_MODE=gemini
GEMINI_API_KEY=<server-side-only>
SNAPINSIGHT_ALLOW_MOCK_FALLBACK=false   # unless testing resilience
```

Redeploy Render. Redeploy Vercel only if public env changed.

Verify `/health` shows `analysis_mode: gemini` and `gemini_configured: true` (boolean presence only).

---

## Activate Gemini Live later (owner)

1. Complete Gemini analysis testing first.
2. On Render:
   - `SNAPINSIGHT_GEMINI_LIVE_ENABLED=true`
   - `GEMINI_API_KEY` present
   - `SNAPINSIGHT_LIVE_ACCESS_CODE` set (recommended)
3. Redeploy Render.
4. Confirm `/v1/live/config` → `enabled: true` when ready.
5. In UI, enter access code if prompted; start Live session briefly; confirm telemetry only.

See [gemini-live.md](./gemini-live.md).

---

## Troubleshooting links

| Issue | Doc |
|-------|-----|
| API URL / CORS / cold start | [troubleshooting.md](./troubleshooting.md) |
| Deploy env vars | [deploy.md](./deploy.md) |
| Smoke automation | [smoke-test.md](./smoke-test.md) |
| Mock vs gemini vs fallback | [troubleshooting.md](./troubleshooting.md) § D |
| Live disabled vs misconfigured | [troubleshooting.md](./troubleshooting.md) § B |

---

## Related docs

- [screenshots-and-video-checklist.md](./screenshots-and-video-checklist.md)
- [cost-privacy-safety.md](./cost-privacy-safety.md)
- [limitations.md](./limitations.md)
