# SnapInsight troubleshooting

## A. “Analysis service unavailable. Start the backend or check the API URL.”

In Block 19A this user-facing copy was replaced with a more deployment-specific
message, but older previews may still show the original text.

Likely causes:

- Render backend cold start.
- Wrong or missing `NEXT_PUBLIC_SNAPINSIGHT_API_URL`.
- Vercel Preview env scope does not include `NEXT_PUBLIC_SNAPINSIGHT_API_URL`.
- Render CORS does not allow the current frontend origin.
- Backend is actually down.
- Network request is blocked by browser, proxy, or local network policy.

Fixes:

1. Open backend health directly:
   `https://YOUR_BACKEND.onrender.com/health`.
2. Confirm Vercel has `NEXT_PUBLIC_SNAPINSIGHT_API_URL` set for Production and
   Preview, plus Development if needed.
3. Confirm Render `SNAPINSIGHT_ALLOWED_ORIGINS` includes the stable production
   frontend origin.
4. Confirm Render `SNAPINSIGHT_ALLOWED_ORIGIN_REGEX` matches the Vercel Preview
   URL pattern for this project/team.
5. Redeploy Vercel after changing any `NEXT_PUBLIC_*` variable.
6. Redeploy Render after changing CORS env vars.
7. Wait and retry after a Render cold start.

## B. “Could not load Live mode configuration.”

This means the frontend could not fetch `GET /v1/live/config`.

It is different from Gemini Live being disabled. If the backend is reachable and
Live is disabled, `/v1/live/config` should return HTTP 200 with
`enabled=false` and `status="disabled"`.

Likely causes are the same deployment issues as analysis fetch failures:

- missing/wrong `NEXT_PUBLIC_SNAPINSIGHT_API_URL`
- Vercel Preview env variable not set
- Render CORS origin not allowed
- Render cold start
- backend down or network blocked

## C. Gemini Live disabled state

`SNAPINSIGHT_GEMINI_LIVE_ENABLED=false` is expected until activation.

- Disabled is not a failure.
- The panel should show: “Gemini Live is disabled in this deployment
  configuration.”
- The browser should not request camera/microphone permissions.
- The browser should not open a Gemini WebSocket.
- `POST /v1/live/token` should remain blocked while disabled.

## D. Gemini real vs mock vs mock_fallback

- `mock` mode keeps demos and development working without `GEMINI_API_KEY`.
- `gemini` mode is the real analysis path and requires `GEMINI_API_KEY`
  server-side on Render.
- `mock_fallback` is opt-in via `SNAPINSIGHT_ALLOW_MOCK_FALLBACK=true`; if Gemini
  fails and fallback is allowed, the app returns a clearly labeled mock fallback
  instead of breaking the demo.

Do not treat `mock_fallback` as a broken app. It is a visible resilience mode for
controlled demos. Do not require Gemini real mode for smoke checks.

## E. Langfuse/LLMOps troubleshooting

- `/health` and `/v1/metrics/summary` expose safe LLMOps fields:
  `llmops_enabled`, `llmops_configured`, `llmops_provider`, and
  `llmops_environment`.
- Langfuse disabled, missing, or misconfigured should not break analysis, chat,
  compare, graph, Live config, or health checks.
- Traces must not include secrets, media bytes, base64, raw prompts, raw user
  questions, transcripts, OpenFoodFacts raw payloads, tokens, access codes, or
  PII.

## F. CORS preview check

Use an OPTIONS preflight from your terminal:

```bash
curl -sI -X OPTIONS https://YOUR_BACKEND.onrender.com/v1/analyze/image \
  -H "Origin: https://YOUR_PREVIEW.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

Expected result:

- `Access-Control-Allow-Origin` should equal the exact preview origin you sent.
- If it is missing, Render CORS does not allow that preview URL. Check
  `SNAPINSIGHT_ALLOWED_ORIGIN_REGEX`, redeploy Render, and retry.
