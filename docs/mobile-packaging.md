# SnapInsight — Mobile Packaging

SnapInsight ships today as a **mobile-first PWA**. Native app store distribution is **feasible but optional**—not required for technical credibility or portfolio review.

**Status:** Not published to Google Play or Apple App Store.

---

## Why PWA is enough for now

| Benefit | Detail |
|---------|--------|
| Single codebase | Next.js app on Vercel; no store review for each fix |
| HTTPS demo | Share one production URL for hiring and stakeholder demos |
| Installable | Manifest + service worker shell where browsers support install |
| Camera access | `getUserMedia` and file upload work on modern mobile browsers |

Limitations: iOS PWA constraints, no full background processing, store discovery absent.

---

## Android — Trusted Web Activity (TWA) / Bubblewrap

**Recommended first store path** if Play listing is desired.

| Aspect | Notes |
|--------|-------|
| Approach | Wrap the production PWA URL in a TWA using [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap) |
| Pros | One codebase; fast updates via web deploy; Play trust signals |
| Cons | Android-only; Digital Asset Links verification required |
| Readiness | Manifest, icons, and theme colors largely exist; needs store assets and QA |

**Requirements before submission:**

- [ ] Production HTTPS URL stable (Vercel Production)
- [ ] `assetlinks.json` for domain verification
- [ ] High-res launcher icons (adaptive)
- [ ] Splash screens aligned with brand
- [ ] Privacy policy URL (hosted)
- [ ] Camera permission rationale in store listing
- [ ] Backend reliability proof (smoke checks, cold-start awareness)
- [ ] Cost controls documented (`mock` default for public beta if needed)

---

## Capacitor — iOS and Android native wrapper

**Later option** when device APIs or store policies require a native shell.

| Aspect | Notes |
|--------|-------|
| Approach | Capacitor wraps the web app in WebView + native bridge |
| Pros | iOS + Android from one project; optional native plugins |
| Cons | Rebuild per release; App Store review for camera/mic; more maintenance |

Use when PWA limits block a feature—not as the default first step.

---

## App store requirements (both platforms)

| Asset / policy | Purpose |
|----------------|---------|
| App icons (multiple densities) | Store listing and launcher |
| Splash screens | Launch experience |
| Manifest polish | `name`, `theme_color`, `display`, `orientation` |
| Privacy policy | Required for camera/mic and data handling |
| Permission copy | Clear why camera (and mic if Live enabled) is used |
| Store listing | Screenshots, description, content rating |
| Real-device QA | Android + iOS browsers; TWA if applicable |
| Backend reliability | Health, metrics, CORS, cold-start behavior |
| Cost controls | Analysis mode defaults; Live off unless intentional |

---

## Gemini Live and store review

If Gemini Live is activated for a store build:

- Microphone and camera permissions need accurate disclosure.
- Live streams go to Google—not proxied through SnapInsight—but privacy policy must say so.
- Default store candidate builds should keep Live **disabled** until policies are reviewed.

See [gemini-live.md](./gemini-live.md).

---

## What is **not** claimed

- SnapInsight is **not** currently listed on Play Store or App Store.
- TWA/Capacitor paths are **documented plans**, not completed submissions.

---

## Related docs

- [scaling-roadmap.md](./scaling-roadmap.md)
- [demo-guide.md](./demo-guide.md)
- [cost-privacy-safety.md](./cost-privacy-safety.md)
- [screenshots-and-video-checklist.md](./screenshots-and-video-checklist.md)
