# SnapInsight — Screenshots & Video Checklist

**Status:** Placeholders only. No image or video files are committed in Block 20A. Capture from **Production** PWA and owner backend when ready.

---

## Before capture

- [ ] Confirm canonical frontend URL (Vercel Production)
- [ ] Confirm backend health, metrics, Live disabled (`GET /v1/live/config`)
- [ ] Choose demo mode (`mock` for UI polish shots; `gemini` for real analysis shots—label accordingly)
- [ ] Use non-sensitive sample products only
- [ ] Redact any env secrets from screenshots

---

## Screenshots to capture later

| # | Screen | Notes |
|---|--------|-------|
| 1 | Landing / home | Mobile viewport first |
| 2 | Scan / upload | Camera + file picker visible |
| 3 | Analysis result | Product card with confidence |
| 4 | Citations / grounding | OFF source visible when matched |
| 5 | Contextual chat | Follow-up on same product |
| 6 | Compare mode | Two products side by side |
| 7 | Product graph | GraphRAG Lite view |
| 8 | Status / metrics | In-app or `/v1/metrics/summary` |
| 9 | Langfuse trace | Safe metadata fields only |
| 10 | Gemini Live disabled panel | `enabled: false` in UI |
| 11 | Desktop width | Optional—show responsive layout |

**Suggested export paths (when created):**

- `docs/assets/screenshots/01-landing-mobile.png`
- `docs/assets/screenshots/02-scan-upload.png`
- … (consistent numbering)

Do not commit until reviewed for privacy and accuracy.

---

## Video demo outline (90–120 seconds)

| Segment | Duration | Content |
|---------|----------|---------|
| Hook | 0:00–0:10 | Problem: label overload; SnapInsight tagline |
| Scan | 0:10–0:25 | Capture/upload product image |
| Result | 0:25–0:40 | Insight card + citations |
| Chat | 0:40–0:55 | One contextual follow-up question |
| Compare | 0:55–1:10 | Two products compared |
| Graph | 1:10–1:20 | Quick graph view |
| Ops | 1:20–1:35 | Langfuse trace OR metrics panel (safe fields) |
| Close | 1:35–1:50 | Architecture: modes, privacy, Live disabled by default |

**Honesty beats:** State if recording used `mock` mode. Do not imply Play Store listing or measured ROI.

---

## Post-production checklist

- [ ] Caption mode used (`mock` / `gemini`)
- [ ] No API keys, access codes, or personal data visible
- [ ] Disclaimers audible or on-screen (not medical advice)
- [ ] Link to live demo URL in description
- [ ] Host video externally (e.g. unlisted) — do not bloat git with binaries

---

## Related docs

- [demo-guide.md](./demo-guide.md)
- [mobile-packaging.md](./mobile-packaging.md)
- [README.md](../README.md)
