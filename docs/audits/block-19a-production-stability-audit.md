# Block 19A production stability audit

## Cause of current preview/deployment issue

The deployed core flows are sound, but preview deployments can fail before they
reach product logic:

- Render CORS previously supported exact origins only, so random Vercel Preview
  origins were not supportable without manual allowlist updates.
- Vercel Preview builds also need `NEXT_PUBLIC_SNAPINSIGHT_API_URL`; production
  build behavior alone is not enough.
- Render cold starts can look like backend/API unavailability.
- Existing frontend copy did not distinguish backend/API/CORS/cold-start failures
  from Gemini or Gemini Live failures.

## What Block 19A fixed

- Added env-driven `SNAPINSIGHT_ALLOWED_ORIGIN_REGEX` support for scoped Vercel
  Preview CORS while keeping exact `SNAPINSIGHT_ALLOWED_ORIGINS` and no wildcard
  default.
- Added loopback local frontend CORS default for `127.0.0.1:3000`.
- Clarified analysis and Gemini Live config fetch errors.
- Expanded smoke checks for health, metrics, Live config, graph, CORS preflight,
  retries, and no-secret response checks.
- Added focused CORS, fallback, and deployment-copy tests.
- Documented Vercel Production/Preview env scoping, Render CORS regex strategy,
  cold-start troubleshooting, and disabled-safe Gemini Live behavior.

## Gemini Live status

Gemini Live remains implemented but disabled by default. `GET /v1/live/config`
returns a safe disabled state, `POST /v1/live/token` stays blocked while
disabled, and the browser should not open a WebSocket unless Live config is
ready and a token is returned.

## What remains for Block 19B/future

- Visual/product polish and accessibility pass.
- Broader browser E2E coverage.
- Auth/rate limiting for public operational endpoints before real-user scale.
- Shared Live session guardrails for multi-instance deployments.
- Magic-byte image validation.
- CI workflow for backend, frontend, evals, and smoke checks.
