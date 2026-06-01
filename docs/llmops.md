# SnapInsight LLMOps with Langfuse

Block 18D adds optional backend Langfuse tracing for important SnapInsight API
flows. It is lightweight operational observability, not user analytics or a new
runtime dependency for product correctness.

## Required backend environment variables

Set these on the backend host when tracing should be enabled:

| Variable | Notes |
| --- | --- |
| `SNAPINSIGHT_LLMOPS_ENABLED` | Set `true` to enable Langfuse instrumentation. Any other value disables tracing. |
| `LANGFUSE_PUBLIC_KEY` | Required with tracing enabled. Never expose in frontend env. |
| `LANGFUSE_SECRET_KEY` | Required with tracing enabled. Keep server-side only. |
| `LANGFUSE_BASE_URL` | Required with tracing enabled, for example the Langfuse Cloud host URL. |
| `LANGFUSE_TRACING_ENVIRONMENT` | Optional safe label such as `render-prod` or `staging`. |

If tracing is disabled, env vars are missing, the SDK is unavailable, or
Langfuse has an error, the backend continues serving normal responses.

## What is traced

The backend emits small Langfuse traces/events for:

- `POST /v1/analyze/image`
  - mode: `gemini`, `mock`, `mock_fallback`, or `error`
  - model name when already non-secret
  - total latency
  - cache hit/miss marker
  - OpenFoodFacts grounding status
  - citation and warning counts
  - fallback and high-level error status
- `POST /v1/chat/product`
  - mode and fallback status
  - message count, question length, product-context presence
  - citation and warning counts
  - total latency and high-level error status
- `POST /v1/compare/products`
  - diff count, citation count, warning count
  - total latency and high-level error status
- `POST /v1/graph/product`
  - graph backend selected: Neo4j, in-memory, or Neo4j fallback
  - node, edge, and evidence-path counts
  - total latency and high-level error status
- Gemini Live backend events
  - token creation status, model, configured/enabled flags, session limits, and
    high-level error type
  - client lifecycle telemetry: started, connected, ended, error, duration,
    frame count, text-message count, audio/vision flags, and status

`GET /health` and `GET /v1/metrics/summary` expose only precomputed safe status:

- `llmops_enabled`
- `llmops_configured`
- `llmops_provider`
- `llmops_environment`

These endpoints never make live Langfuse network calls.

## What is intentionally not traced

Langfuse metadata must not include:

- image bytes, raw uploads, base64, filenames, EXIF, or image hashes
- audio bytes or browser voice data
- raw user questions, full chat messages, prompts, or model prompt text
- OpenFoodFacts raw payloads
- product compare payloads or full analysis JSON
- secrets, API keys, authorization headers, database credentials, or PII
- personal/private product notes
- Gemini Live transcripts, raw speech/text, ephemeral token values, or access codes

The backend wrapper applies an allowlist to metadata before enqueueing any
Langfuse event so accidental unsupported fields are dropped.

## Disable tracing

Set:

```bash
SNAPINSIGHT_LLMOPS_ENABLED=false
```

or remove one of the required Langfuse env vars. The app should continue working
with `llmops_configured=false`.

## Troubleshooting

- `/health` shows `llmops_enabled=false`: confirm `SNAPINSIGHT_LLMOPS_ENABLED=true`.
- `/health` shows `llmops_enabled=true` and `llmops_configured=false`: confirm all
  required Langfuse env vars are present and the `langfuse` package installed.
- Langfuse Cloud outage or slow network: API responses and Render health checks
  should remain normal because request handlers only enqueue SDK events and never
  flush or validate Langfuse live.
- See [`troubleshooting.md`](./troubleshooting.md) for deployment/API/CORS
  issues that can look like product or Gemini failures.

## Manual verification checklist

1. Confirm Render has:
   - `SNAPINSIGHT_LLMOPS_ENABLED=true`
   - `LANGFUSE_PUBLIC_KEY`
   - `LANGFUSE_SECRET_KEY`
   - `LANGFUSE_BASE_URL`
   - optional `LANGFUSE_TRACING_ENVIRONMENT`
2. Redeploy the backend.
3. Call `/health` and confirm `llmops_enabled=true`,
   `llmops_configured=true`, and `llmops_provider="langfuse"`.
4. Run a real `/v1/analyze/image` request and confirm a Langfuse trace/event
   appears for analysis.
5. Run chat and compare from an existing analysis result and confirm traces/events
   appear.
6. Set `SNAPINSIGHT_LLMOPS_ENABLED=false`, redeploy, and confirm requests still
   work with tracing disabled.

Live Product Session Lite is browser/client-side for this block unless a backend
request is made through the existing chat/analyze/compare/graph endpoints. The
offline tuning pipeline remains reference documentation and is not runtime traced.
