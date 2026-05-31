# Gemini Live Full Integration

Block 18E adds a real Gemini Live voice + vision + text path that is disabled by
default until the deployment owner enables it. Normal analyze, chat, compare,
graph, and Live Session Lite flows do not depend on Gemini Live.

## Architecture

SnapInsight uses a client-to-Gemini WebSocket architecture with backend-minted
ephemeral tokens:

1. The browser requests safe public Live config from `GET /v1/live/config`.
2. When the user taps Start, the browser asks the backend for an ephemeral token
   via `POST /v1/live/token`.
3. The FastAPI backend uses `GEMINI_API_KEY` server-side with
   `client.auth_tokens.create()` and `http_options={"api_version": "v1alpha"}`.
4. The backend locks model, response modality, output transcription, and safe
   system instruction into `liveConnectConstraints`.
5. The browser opens the constrained Gemini WebSocket returned by the backend and
   appends `?access_token={token}`.
6. Live audio, camera frames, and text go directly from the browser to Gemini,
   not through Render.
7. The browser sends only safe lifecycle telemetry to
   `POST /v1/live/telemetry`.

The frontend never receives `GEMINI_API_KEY` or the Live access code.

## Backend environment variables

| Variable | Default | Notes |
| --- | --- | --- |
| `SNAPINSIGHT_GEMINI_LIVE_ENABLED` | `false` | Must be `true` to mint tokens. |
| `GEMINI_API_KEY` | unset | Required server-side when Live is enabled. |
| `SNAPINSIGHT_GEMINI_LIVE_MODEL` | `gemini-3.1-flash-live-preview` | Model locked into the ephemeral token. |
| `SNAPINSIGHT_LIVE_ACCESS_CODE` | unset | Optional but strongly recommended before enabling. If set, token requests must provide it. |
| `SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS` | `120` | Client and token expiry guardrail. |
| `SNAPINSIGHT_LIVE_MAX_FRAMES_PER_SECOND` | `1` | Camera frame snapshot rate cap. |
| `SNAPINSIGHT_LIVE_AUDIO_ENABLED` | `true` | Enables microphone input and audio responses. |
| `SNAPINSIGHT_LIVE_VISION_ENABLED` | `true` | Enables camera-frame input. |
| `SNAPINSIGHT_LIVE_SYSTEM_INSTRUCTION` | safe SnapInsight default | Optional server-side instruction locked into token constraints. |

## Ephemeral token settings

The backend mints tokens with:

- `uses=1`
- `new_session_expire_time = now + 90 seconds`
- `expire_time = now + SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS + 60 seconds`
- constrained endpoint:
  `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained`
- `liveConnectConstraints.model` set from `SNAPINSIGHT_GEMINI_LIVE_MODEL`
- `config.response_modalities=["AUDIO"]`
- `config.output_audio_transcription={}`
- server-side `config.system_instruction`

The token response returns only:

- token name string
- constrained WebSocket URL
- `expires_in_seconds=90`
- modality label: `audio_with_transcription`
- safe public session limits and feature flags

It never returns `GEMINI_API_KEY`, access code, full token objects, or internal
credentials.

## Frontend behavior

- Camera and microphone permissions are requested only after the user starts a
  Live session.
- The browser uses the `websocket_url` returned by `/v1/live/token`; it does not
  hardcode the Gemini endpoint in application code.
- The first WebSocket message is `setup: {}`. System instruction is not sent from
  the frontend because it is locked into the token.
- Text turns are sent as `clientContent`.
- Camera frames are JPEG snapshots capped by backend config, default 1 FPS.
- Microphone input is converted to PCM chunks in-browser and sent directly to
  Gemini.
- Audio responses are played when AudioContext supports PCM playback.
- Output transcripts are always displayed as text fallback.
- Stop, navigation, unmount, or timeout closes WebSocket, stops all media tracks,
  clears timers, and closes audio contexts.

## Privacy guarantees

SnapInsight does not persist Live sessions. The backend does not receive or log:

- audio bytes
- video
- image frames
- base64 media
- transcripts
- raw user text
- raw speech
- model audio/text response content
- access codes
- ephemeral token values
- API keys

Live media is sent directly from the browser to Gemini using the short-lived
ephemeral token.

## Safe telemetry and Langfuse

`POST /v1/live/telemetry` accepts only:

- `live_session_started`
- `live_session_connected`
- `live_session_ended`
- `live_session_error`
- duration seconds
- frames sent count
- audio/vision enabled booleans
- text message count
- model
- status/error type

The backend forwards only allowlisted aggregate metadata to the existing LLMOps
wrapper. Unsafe fields such as transcripts or base64 media are rejected by the
telemetry schema and are never traced.

## Cost and rate guardrails

- Live is disabled by default.
- Access code is optional but strongly recommended before enabling.
- Session duration defaults to 120 seconds.
- Camera frames default to 1 FPS.
- Ephemeral tokens are single-use.
- A small in-memory per-process guardrail limits token creation cooldown and
  approximate active token windows.

Known limitation: the in-memory session guardrail operates per Render process. On
Render free/starter single-instance deployments this is effective. On multi-
instance deployments, a shared store such as Redis would be needed for global
limits; that is intentionally out of scope for Block 18E.

## Activation after Block 20

1. In Render, set `SNAPINSIGHT_GEMINI_LIVE_ENABLED=true`.
2. Ensure `GEMINI_API_KEY` is set server-side.
3. Set `SNAPINSIGHT_LIVE_ACCESS_CODE` to a private operator-provided code.
4. Confirm optional session limits:
   - `SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS=120`
   - `SNAPINSIGHT_LIVE_MAX_FRAMES_PER_SECOND=1`
5. Redeploy Render.
6. Redeploy Vercel only if frontend public env changed. No Gemini key or access
   code should be added to Vercel `NEXT_PUBLIC_*` env vars.
7. Open the app and go to Scan.
8. In Gemini Live Voice + Vision, enter the access code and start a Live session.
9. Confirm `/health` shows:
   - `gemini_live_enabled=true`
   - `gemini_live_configured=true`
   - `gemini_live_provider="gemini_live"`
10. Confirm Langfuse receives safe Live token/telemetry events.

## Manual QA checklist

- Disabled deployment shows “Live mode is disabled in this deployment
  configuration.”
- Enabled deployment without `GEMINI_API_KEY` shows not configured and token
  request fails safely.
- Wrong/missing access code is rejected and not logged.
- Correct access code creates a token and opens the constrained WebSocket.
- Browser prompts for camera/microphone only after Start.
- Text input sends to Live session.
- Camera frames are sent at configured FPS.
- Microphone streaming works where browser Web Audio APIs are available.
- Audio playback works where supported; transcript fallback remains visible if
  audio playback fails.
- Stop and page navigation release camera/microphone indicators.
- Langfuse telemetry contains counts/status only, never media or transcript
  content.
