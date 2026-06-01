# SnapInsight — Scaling Roadmap

A phased plan for growing SnapInsight from the current deployed MVP toward a commercial-grade product intelligence platform. Phases are **technical sequencing**, not calendar commitments.

**Principle:** Do not overbuild infrastructure before traffic and product-market signal justify it.

---

## Phase 1 — Current state (today)

**What exists:**

- Next.js PWA on Vercel + FastAPI on Render
- Core flows: analyze, chat, compare, graph, metrics, smoke checks
- Open Food Facts grounding + enrichment
- In-memory cache/metrics (process-local)
- Optional Langfuse; Gemini Live disabled-safe
- `mock` / `gemini` / `mock_fallback` analysis modes

**Trade-offs accepted:**

- No accounts, payments, or persistent user history
- Single-process cache not shared across instances
- Exact-byte cache keys (not perceptual dedup yet)

**Do not overbuild yet:** Multi-region, dedicated vector cluster, enterprise SSO.

---

## Phase 2 — Controlled Gemini activation

**Goals:**

- Enable `gemini` in production with spend caps and monitoring
- Keep `mock` for CI and low-cost demos
- Use `mock_fallback` only in controlled windows

**Needs:**

- Owner runbook ([demo-guide.md](./demo-guide.md))
- Langfuse dashboards for `analysis_mode`, `latency_ms`, `fallback_used`
- Alerting on fallback rate spikes (external to app today)

**Trade-off:** Real per-request cost vs. demo predictability.

---

## Phase 3 — Improved product matching and data coverage

**Goals:**

- Higher citation/grounding coverage in weak OFF categories
- Better barcode/visual matching pipeline
- Optional curated SKU subset for demos

**Options:**

- Supplemental dataset with same citation UX
- Perceptual cache keys for repeat captures
- Eval suite expansion beyond offline fixtures

**Do not overbuild:** Full proprietary product graph before measuring OFF gap analysis.

---

## Phase 4 — Saved comparisons / history (privacy-first)

**Goals:**

- Optional user history for compare sessions and recent scans
- Clear retention policy and delete controls

**Needs:**

- Auth (even lightweight magic link)
- Encrypted storage; **no raw image retention by default**
- GDPR-style export/delete if B2C

**Trade-off:** Convenience vs. privacy surface area.

---

## Phase 5 — Android packaging (TWA / Bubblewrap)

**Goals:**

- Play Store presence without rewriting the app
- Same backend contract; manifest polish

See [mobile-packaging.md](./mobile-packaging.md).

**Do not overbuild:** iOS native shell until Android path is validated.

---

## Phase 6 — Capacitor iOS / Android wrapper

**Goals:**

- Deeper device APIs if PWA limits block features
- Unified store binaries

**Costs:**

- Store review cycles, rebuild discipline, permission copy
- Separate QA matrix per OS version

---

## Phase 7 — B2B dashboard / public API

**Goals:**

- Team workspaces, export, API keys, usage billing
- SLAs and rate limits on public endpoints

**Needs:**

- Shared rate limiting (Redis or API gateway)
- Audit logs, admin roles
- Documentation portal separate from consumer PWA

---

## Phase 8 — Stronger evals, rate limiting, Sentry, always-on backend

**Goals:**

- CI running evals + smoke on every deploy
- Sentry (or equivalent) for frontend/backend errors
- Paid Render tier or alternative to reduce cold starts
- Shared session guardrails for Gemini Live multi-instance

**Trade-off:** Fixed hosting cost vs. free-tier cold start UX.

---

## Phase 9 — More verticals beyond CPG

**Goals:**

- Adjacent packaged goods (cosmetics, supplements with stricter copy guardrails)
- Vertical-specific datasets and disclaimers

**Risk:** Weakening focus before CPG grounding metrics are strong.

---

## What not to overbuild (summary)

| Temptation | Why wait |
|------------|----------|
| Dedicated vector DB at MVP scale | OFF + structured matching may suffice |
| GraphRAG at enterprise scale | Lite graph proves concept; expand with data |
| Gemini Live on by default | Cost and media compliance |
| Native iOS + Android simultaneously | PWA + TWA first |
| Guaranteed ROI dashboards | Instrument honestly first |

---

## Related docs

- [business-case.md](./business-case.md)
- [mobile-packaging.md](./mobile-packaging.md)
- [roadmap.md](./roadmap.md)
- [product/snapinsight-business-product-brief.md](./product/snapinsight-business-product-brief.md)
