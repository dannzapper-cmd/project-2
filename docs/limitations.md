# SnapInsight — Limitations

Honest limitations are part of the product design. This document states what SnapInsight is **not**, what users should expect in production today, and what remains intentionally deferred.

---

## Product scope

| Area | Limitation |
|------|------------|
| Medical | **Not medical advice.** No diagnosis, treatment, or personalized clinical guidance. |
| Health claims | Informational nutrition/ingredient context only. Users must verify against the physical label. |
| Recommendations | **Not a guaranteed product recommendation engine.** Outputs are assistive, not authoritative purchase directives. |
| Counterfeits | No authenticity or counterfeit detection. |
| Pricing | No real-time price scraping or purchase guarantees. |
| Legal | Does not replace regulatory label review for manufacturers. |

---

## Data and grounding

- **Open Food Facts coverage is uneven.** Community-contributed data can be incomplete, outdated, or wrong in some regions and categories. Citations show provenance; they do not guarantee correctness.
- **Community dataset risks:** Anyone can contribute to Open Food Facts. SnapInsight surfaces matches conservatively but cannot audit every record.
- **No guaranteed product identification.** Visual similarity, poor lighting, obscure brands, and dataset gaps can produce wrong or partial matches.
- **Confidence and fallback UX** (possible matches, retake photo, visible modes) are intentional product behavior—not bugs to hide.

---

## AI and model behavior

- Multimodal models can **hallucinate** fields not visible on the package.
- Grounding reduces but does not eliminate hallucination; retrieval misses still occur.
- Structured JSON can be **confidently wrong**; the UI must surface uncertainty.
- **Image quality dependency:** blur, glare, partial labels, and shelf clutter reduce accuracy.

---

## Analysis modes (`mock` / `gemini` / `mock_fallback`)

SnapInsight runs three explicit analysis modes. This is intentional maturity, not a hidden shortcut.

| Mode | What it means |
|------|----------------|
| `mock` | Deterministic demo path. No Gemini call. Used for local dev, CI, and low-cost demos. |
| `gemini` | Real multimodal analysis when `GEMINI_API_KEY` is configured server-side. |
| `mock_fallback` | Opt-in resilience when Gemini fails but `SNAPINSIGHT_ALLOW_MOCK_FALLBACK=true`. Response is visibly labeled; fallback results are **not** cached. |

**Why mock exists:** Safe demos, predictable CI, zero API spend, and honest stakeholder walkthroughs without implying live model quality.

**Why mock_fallback exists:** Graceful degradation during controlled production testing—not silent failure.

Gemini and Gemini Live are **not activated** in the default deployment configuration documented for Block 19A/20A. Activation requires explicit owner action (see [demo-guide.md](./demo-guide.md), [deploy.md](./deploy.md)).

---

## Gemini Live

- Full Gemini Live integration is **implemented** but **disabled by default** (`SNAPINSIGHT_GEMINI_LIVE_ENABLED=false`).
- Activation pending controlled testing, access-code guardrails, and cost review.
- Live audio/vision streams go browser-to-Gemini; SnapInsight does not proxy media.

See [gemini-live.md](./gemini-live.md).

---

## Privacy, persistence, and accounts

- **No accounts, payments, or enterprise auth** in the current product.
- **No persistent user profile or saved history** across sessions (in-memory cache/metrics only; process-local).
- Images are processed for analysis and **not stored** as uploaded files on the server.
- Chat, compare, and session payloads are **not persisted** server-side for user history.

See [cost-privacy-safety.md](./cost-privacy-safety.md).

---

## Distribution and packaging

- **No native App Store or Play Store distribution yet.** The product ships as a PWA (installable where supported).
- Android TWA/Capacitor paths are documented as feasible but optional ([mobile-packaging.md](./mobile-packaging.md)).

---

## Operational and hosting

- **Render free-tier cold starts** can add latency on first request after idle; smoke scripts retry transient failures.
- In-memory **cache and metrics reset** on backend restart and are not shared across workers.
- Process-local rate limits and Live session guardrails are not multi-instance safe without shared infrastructure (future).
- Hobby or free hosting tiers may pause or throttle—verify provider terms before commercial SLA claims.

---

## Deferred or out-of-scope capabilities

| Capability | Status |
|------------|--------|
| Full live camera streaming (WebRTC-heavy) | Deferred |
| Large-scale GraphRAG beyond Lite | Partial (Neo4j optional) |
| Dedicated vector DB / pgvector pipeline | Not implemented; OFF API + structured matching today |
| Local fine-tuning as primary intelligence | Non-goal |
| Advanced offline voice | Browser Voice Lite only |

---

## User-facing disclaimers (in app)

The product includes variants of:

- This is not medical advice. Consult qualified professionals for health decisions.
- Data may come from Open Food Facts. Always check the physical product label.
- Identification may be wrong. Confirm before relying on this information.

Exact commercial copy should receive legal review before a public launch.

---

## Related docs

- [cost-privacy-safety.md](./cost-privacy-safety.md)
- [business-case.md](./business-case.md)
- [demo-guide.md](./demo-guide.md)
- [troubleshooting.md](./troubleshooting.md)
