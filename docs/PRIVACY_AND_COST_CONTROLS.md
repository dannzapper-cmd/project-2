# Privacy and cost controls

Why SnapInsight limits public demo usage, what is stored, and how to tune controls.

Related: [ENV_VARS.md](./ENV_VARS.md) · [cost-privacy-safety.md](./cost-privacy-safety.md) · [limitations.md](./limitations.md)

---

## Why limits exist

The cost-controlled public demo uses **real Gemini** when configured. Without caps, a shared URL could incur unbounded API spend. Limits protect the deployment owner while keeping the product usable for portfolio review.

Users see a clear HTTP `429` message when a limit is reached — not a crash.

---

## Session limits

Keyed by `X-SnapInsight-Session-Id` (auto-generated in the PWA `sessionStorage`).

| Control | Default env | Behavior |
|---------|-------------|----------|
| Analyses per session | `SNAPINSIGHT_MAX_ANALYSES_PER_SESSION=5` | Counts all analysis attempts (including cache hits) |
| Chat messages per session | `SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION=10` | Per follow-up question |
| Compare per session | `SNAPINSIGHT_MAX_COMPARE_PER_SESSION=3` | Side-by-side comparisons |

**Refresh the page** to start a new browser session id.

---

## Daily limits (process-local)

| Control | Default env | Behavior |
|---------|-------------|----------|
| Analyses per UTC day | `SNAPINSIGHT_DAILY_ANALYSIS_LIMIT=100` | Global per backend process |
| Estimated Gemini spend | `SNAPINSIGHT_DAILY_COST_LIMIT_USD=5` | Conservative estimate before/after real Gemini calls — **not** Google billing |

**Limitation:** counters reset on backend restart and are **not shared** across Render instances or workers. Multi-instance production would need Redis/DB (future).

---

## Cache

| Env | Default | Purpose |
|-----|---------|---------|
| `SNAPINSIGHT_CACHE_ENABLED` | `true` | In-memory LRU of analysis **responses** only |
| `SNAPINSIGHT_CACHE_TTL_SECONDS` | `900` | 15 minutes |
| `SNAPINSIGHT_CACHE_MAX_ENTRIES` | `50` | Cap entries per process |

- Keys: SHA256(image bytes + mode + model) — not reversible to image bytes
- **Fallback results are never cached**
- Cache reduces duplicate Gemini cost/latency

---

## API keys

- `GEMINI_API_KEY` is **backend-only** (Render secret)
- Never in frontend, logs, Langfuse traces, or git
- Frontend only knows `gemini_configured: true/false` from `/health`

---

## Images and audio

| Data | Retained by SnapInsight? |
|------|--------------------------|
| Uploaded/captured images | **No** persistent storage |
| EXIF metadata | Stripped in browser where supported (Canvas re-encode); HEIC fallback documented |
| Voice Lite audio | Browser speech APIs only — **not sent** to backend |
| Chat / compare payloads | Processed in-memory per request — **no** server DB |
| Gemini Live media (if ever enabled) | Direct browser ↔ Gemini; not persisted on SnapInsight |

---

## Safety boundaries

- No medical diagnosis or absolute health claims
- No counterfeit / authenticity assertions
- Open Food Facts citations when matched; uncertainty shown when not
- User must verify physical labels for allergens and nutrition decisions

---

## Tuning limits

**Tighter demo (lower cost):**

```bash
SNAPINSIGHT_MAX_ANALYSES_PER_SESSION=3
SNAPINSIGHT_DAILY_ANALYSIS_LIMIT=50
SNAPINSIGHT_DAILY_COST_LIMIT_USD=2
```

**Local dev (no Gemini spend):**

```bash
SNAPINSIGHT_ANALYSIS_MODE=mock
```

**Disable mock fallback in production:**

```bash
SNAPINSIGHT_ALLOW_MOCK_FALLBACK=false
```

Monitor: `GET /v1/metrics/summary` → `usage_limits_*` fields and `counters.usage_limit_hits`.

---

## Test limits locally

```bash
cd backend
SNAPINSIGHT_ANALYSIS_MODE=mock \
SNAPINSIGHT_MAX_ANALYSES_PER_SESSION=2 \
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Three analyses with the same `X-SnapInsight-Session-Id` → third returns `429` / `session_analysis_limit`.
