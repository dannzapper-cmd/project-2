# Screenshot Capture Guide

Reproducible evidence capture for SnapInsight using Playwright.

## Command

```bash
npm install
npx playwright install chromium
npm run evidence:screenshots
```

## Environment variables (optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SNAPINSIGHT_EVIDENCE_BASE_URL` | `https://project-2-wine-seven.vercel.app` | Frontend to capture |
| `SNAPINSIGHT_EVIDENCE_BACKEND_HEALTH_URL` | `https://snapinsight-backend-87dm.onrender.com/health` | Backend warm-up target |

Do **not** set or commit API keys, Live access codes, or auth tokens for capture.

## What the script does

1. **Warms backend** — Retries `/health` up to 6 times (Render cold start).
2. **Generates synthetic demo labels** — Non-branded PNGs saved to `docs/evidence/demo-assets/`.
3. **Runs production flows** — Upload → Analyze → wait for real Gemini result.
4. **Captures mobile and desktop screenshots** — See `docs/evidence/screenshots/README.md`.
5. **Captures dedicated routes** — After scan + localStorage persistence, navigates to `/insights`, `/compare`, and `/activity` for screenshots (verified post PR #30).
6. **Captures graph and Live on `/scan`** — Evidence graph and Gemini Live gated UI from the scan workflow.
7. **Creates preview thumbnail** — `docs/evidence/preview/scan-result-preview.png`.

## Output locations

```
docs/evidence/
├── demo-assets/          # Synthetic product label PNGs
├── preview/              # Optional thumbnail
└── screenshots/
    ├── mobile/           # 7 mobile captures
    ├── desktop/          # 5 desktop captures
    └── README.md         # Manifest (auto-updated on success)
```

## Manual re-run (cold backend)

If capture fails during warm-up or analysis:

1. Open https://snapinsight-backend-87dm.onrender.com/health in a browser and wait for JSON with `"analysis_mode":"gemini"`.
2. Re-run `npm run evidence:screenshots`.

The in-app banner shows **"Backend waking up · Try again in a few seconds"** during cold start — this is expected on Render free tier.

## If Gemini analysis fails

The script **stops** and prints the error. Do not:

- Fabricate screenshots
- Edit the DOM to fake results
- Enable mock fallback

Common causes:

- Backend still waking
- Session analysis limit reached (5 per session)
- Daily cost limit reached
- Transient Gemini API error

Wait or use a fresh browser session (new client session ID) and retry.

## Gemini Live screenshots

- Captures the **ready / access-code-gated** UI only.
- Does **not** start a Live session unless you explicitly provide a secure local env var (not committed).
- Never screenshot access codes or tokens.

## Privacy and secrets

- No real user images
- No API keys in screenshots, logs, or committed files
- Synthetic labels only
- Compare uses analysis JSON — no image bytes in compare requests

## CI / headless environments

Playwright requires Chromium:

```bash
npx playwright install chromium
```

If the environment cannot run browsers (e.g. some cloud sandboxes), commit the script and docs; generate screenshots locally and include PNGs in your PR.
