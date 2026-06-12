# Roadmap — next steps

What comes **after** Proyecto 2 / portfolio close-out. Nothing below is claimed as shipped unless explicitly marked.

---

## Not in this close-out

| Item | Status |
|------|--------|
| Gemini Live in production | **Not activated** — budget/credits; code exists but `SNAPINSIGHT_GEMINI_LIVE_ENABLED=false` |
| Google Play Store listing | **Not published** — readiness documented only |
| Apple App Store listing | **Not published** — readiness documented only |
| Professional packaging notebooks | **Not created yet** — future, Play/App Store only |
| User accounts / payments | Out of scope |
| Shared Redis rate limiting | Future scale item |

---

## Optional wow — Gemini Live (experimental)

- Real-time multimodal hints via WebSocket to Gemini
- Backend mints short-lived ephemeral tokens; browser never gets `GEMINI_API_KEY`
- Activation docs: [gemini-live.md](./gemini-live.md)
- **Recommendation:** keep disabled until dedicated budget and access controls

---

## Mobile store readiness

Documented path (not executed in this close-out):

1. **PWA** — current state (installable where supported)
2. **Android TWA** — Trusted Web Activity wrapper toward Play Store
3. **Capacitor** — when native APIs exceed PWA limits

See [MOBILE_STORE_READINESS.md](./MOBILE_STORE_READINESS.md) · [mobile-packaging.md](./mobile-packaging.md)

---

## Future notebooks (explicit scope)

When requested, create **professional notebooks only** for:

- Google Play Store packaging readiness (TWA / signing / asset checklist)
- Apple App Store packaging readiness (Capacitor / TestFlight checklist)

**Not planned:** extra eval notebooks, ad-hoc experiments, or tuning demos unless explicitly requested.

---

## Engineering scale (honest)

From [scaling-roadmap.md](./scaling-roadmap.md):

- Shared cache + rate limits (Redis)
- Perceptual hash near-duplicate cache
- Stronger evals and production metrics
- Auth and per-user quotas if productized

---

## Portfolio positioning language

Use:

- “production-like deployed demo”
- “cost-controlled public demo”
- “mobile-first PWA”
- “store-readiness documented”
- “Gemini Live planned as experimental next step”

Avoid:

- “published on App Store / Play Store” (unless actually published)
- “enterprise-grade at scale” without shared infra
- “real-time Gemini Live live in demo” (disabled in close-out)
