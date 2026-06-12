# Mobile store readiness

SnapInsight ships today as a **mobile-first PWA**. Play Store and App Store listings are **not published** in Proyecto 2. This document states readiness posture and the documented path forward.

Related: [mobile-packaging.md](./mobile-packaging.md) · [ROADMAP_NEXT_STEPS.md](./ROADMAP_NEXT_STEPS.md)

---

## Current state

| Platform | Status |
|----------|--------|
| Mobile web / PWA | **Deployed** — responsive UI, camera/upload, installable where browsers support |
| Android (Play Store) | **Not listed** — TWA path documented |
| iOS (App Store) | **Not listed** — Capacitor path documented |

---

## Android — Google Play (future)

**Recommended first store path:** Trusted Web Activity (TWA)

1. Stable HTTPS production URL (Vercel)
2. Digital Asset Links (`assetlinks.json`)
3. Android Studio / Bubblewrap wrapper project
4. Play Console listing assets (screenshots, privacy policy, content rating)
5. Internal testing track before production

**Future notebook scope (when requested):** Play packaging checklist only — signing, TWA config, store assets.

---

## iOS — App Store (future)

**When PWA limits block a requirement:** Capacitor wrapper

1. Capacitor shell around Next.js export or hosted WebView
2. Apple Developer account + provisioning
3. App Store Connect metadata and review guidelines (camera permission copy)
4. TestFlight before App Store

**Future notebook scope (when requested):** App Store packaging checklist only.

---

## What works in PWA today

- Camera capture (`getUserMedia`) on supported mobile browsers
- Image upload + client-side EXIF strip (where Canvas decode works)
- Touch-friendly scan → result → chat → compare flow
- Offline: limited (network required for analysis API)

---

## Known PWA gaps (honest)

- iOS HEIC may skip EXIF strip (documented in `image-preprocess.ts`)
- No push notifications or background sync
- Install prompts vary by browser/OS
- Gemini Live not active in close-out demo

---

## Screenshots / video

Placeholder checklist: [screenshots-and-video-checklist.md](./screenshots-and-video-checklist.md)

---

## Do not claim

- “Available on Play Store / App Store” until actually published
- “Native app” unless a store build exists
- Store notebooks as part of this close-out (not created yet)
