# Final QA audit — SnapInsight close-out

**Audit date:** 2026-06-13 (post-merge evidence refresh)  
**Scope:** Production route verification, evidence recapture, security/privacy audit  
**Prior close-out:** 2026-06-12 (`cursor/final-qa-closeout-c7e6`)

---

## Post-merge verification (PR #30)

| Check | Result |
|-------|--------|
| PR #30 merged to `main` | **PASS** — `ef52e72` |
| Production `/scan` | **PASS** — HTTP 200, no client crash |
| Production `/insights` | **PASS** — dedicated route, latest analysis from localStorage |
| Production `/compare` | **PASS** — dedicated route, two-product compare workflow |
| Production `/activity` | **PASS** — metrics, usage limits, mock fallback disabled |
| Backend `/health` | **PASS** — `gemini`, `mock_fallback_allowed: false`, Live enabled |
| Backend `/v1/metrics/summary` | **PASS** — limits: 5 analyses/session, $5 daily, 10 chat, 3 compare |
| Backend `/v1/live/config` | **PASS** — `requires_access_code: true`, 60s session, 1 FPS |
| `npm run evidence:screenshots` | **PASS** — real Gemini, dedicated routes, no secrets in PNGs |
| Secret scan (grep) | **PASS** — no committed API keys or access codes |
| No `.env` committed | **PASS** |

---

## Executive summary (2026-06-12 baseline)

SnapInsight is **production-like and portfolio-ready** as a cost-controlled mobile-first PWA with real Gemini analysis (when configured), session/daily guardrails, cited grounding, chat, compare, and in-memory observability. Gemini Live is **access-code gated** and experimental. App store publication is **out of scope**.

---

## Checks executed (baseline)

| Check | Command / action | Result |
|-------|------------------|--------|
| Frontend unit tests | `npm test` | **PASS** (20 tests) |
| Frontend lint | `npm run lint` | **PASS** |
| Frontend build | `npm run build` | **PASS** |
| Backend tests | `pytest` (72 tests) | **PASS** |
| Smoke script | `scripts/smoke_check.py` | **PASS** (local mock backend) |
| Secret scan (grep) | `GEMINI_API_KEY` in frontend | **PASS** — backend only |
| `.env` gitignore | `.gitignore` | **PASS** — `.env*` ignored, `.env.example` allowed |
| Usage limits | `test_usage_limits.py` | **PASS** |
| Gemini Live activation | config default | **PASS** — `SNAPINSIGHT_GEMINI_LIVE_ENABLED=false` |

---

## Bugs found & fixes applied

| Issue | Severity | Fix |
|-------|----------|-----|
| Missing portfolio close-out docs | Medium | Added `ENV_VARS`, `DEPLOYMENT`, `PRIVACY_AND_COST_CONTROLS`, `ROADMAP_NEXT_STEPS`, `MOBILE_STORE_READINESS`, `QA_FINAL` |
| No `.env.example` templates | Medium | Added root + `backend/.env.example` |
| Limit errors lacked public-demo context | Low | Backend messages + frontend `getSnapInsightApiErrorMessage` |
| Compare panel syntax error after error-helper edit | High | Fixed stray `})` in catch block |
| README status stale (Block 20A) | Low | Updated for Proyecto 2 close-out |

---

## Desktop checklist

- [x] App builds (`npm run build`)
- [x] Scan page loads static routes
- [x] Upload + analyze flow wired to API
- [x] Error states: deployment unreachable, Gemini unavailable, usage limits
- [x] Chat uses product context only
- [x] Compare uses analysis JSON only (no image bytes)
- [x] Metrics panel reads `/v1/metrics/summary`
- [x] Citations / confidence / warnings visible on result card
- [ ] Full E2E with live Gemini + Open Food Facts — **manual** (requires owner API key)

## Mobile checklist

- [x] Mobile-first layout (Tailwind responsive)
- [x] Camera hook + upload fallback
- [x] EXIF strip via Canvas (non-HEIC)
- [x] Touch-friendly buttons and chat
- [ ] Physical device camera QA — **manual** (owner device)
- [ ] iOS HEIC EXIF limitation — **documented** (`image-preprocess.ts`)

## Deployment checklist

- [x] Render start command documented
- [x] `/health` healthcheck
- [x] CORS env vars documented
- [x] Vercel `NEXT_PUBLIC_SNAPINSIGHT_API_URL` documented
- [x] Smoke script with `BACKEND_BASE_URL` / `FRONTEND_URL`
- [x] Redeploy notes after env changes
- [ ] Owner must set real Vercel + Render URLs in production

## Cost / privacy checklist

- [x] `GEMINI_API_KEY` backend-only
- [x] Session limits (analysis, chat, compare)
- [x] Daily analysis + estimated cost limits
- [x] Cache env-configurable
- [x] No persistent image storage
- [x] Langfuse optional + non-blocking
- [x] No medical / authenticity claims in product scope
- [x] In-memory limit limitation documented

---

## Honest pendientes

1. **Multi-instance Render** — usage limits and cache are per-process; not shared across workers.
2. **Cost limit** — estimated USD, not Google billing API.
3. **Gemini Live** — code exists; **not activated** for budget close-out.
4. **Play / App Store** — readiness documented; **not published**.
5. **Notebooks** — **not created**; future scope is store packaging only.
6. **Metrics endpoint** — unauthenticated (demo); protect before real-user scale.
7. **Manual mobile + live Gemini QA** — requires owner credentials and devices.

---

## Manual test instructions

### Desktop

1. `npm run dev` + backend on `:8000` with `SNAPINSIGHT_ANALYSIS_MODE=mock`
2. Open `/scan` → upload image → verify result card, mode label, citations section
3. Chat → ask about ingredients → verify citations or “limited source” warning
4. Save two analyses → Compare → verify diff table
5. Set `SNAPINSIGHT_MAX_ANALYSES_PER_SESSION=2` → third analysis shows limit message

### Mobile

1. Open deployed Vercel URL on phone (or Chrome DevTools device mode)
2. Test camera permission + capture OR gallery upload
3. Verify readable error if backend cold-start (Render free tier)
4. Verify bottom nav and scan flow without horizontal scroll

### Production Gemini

1. Render: `SNAPINSIGHT_ANALYSIS_MODE=gemini` + `GEMINI_API_KEY`
2. `/health` → `gemini_configured: true`
3. Analyze product image → `mode: "gemini"`

---

## Confirmations

| Statement | Status |
|-----------|--------|
| Gemini Live **not implemented/activated** for close-out | **Confirmed** — disabled by default; documented as next step |
| No notebooks created | **Confirmed** |
| Future notebooks = Play/App store packaging only | **Confirmed** in `ROADMAP_NEXT_STEPS.md` |
| No Play Store / App Store publication | **Confirmed** |

---

## Related docs

- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [ENV_VARS.md](./ENV_VARS.md)
- [PRIVACY_AND_COST_CONTROLS.md](./PRIVACY_AND_COST_CONTROLS.md)
- [smoke-test.md](./smoke-test.md)
