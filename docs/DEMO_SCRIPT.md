# SnapInsight — 60–90 Second Demo Script

**Audience:** Portfolio reviewers, product stakeholders, technical interviewers  
**Production URL:** https://project-2-wine-seven.vercel.app/scan

---

## Opening (10s)

> "SnapInsight is a mobile-first AI visual companion for packaged products. Instead of typing barcodes or reading dense labels, you photograph the package and get structured, cited intelligence."

*Show scan page. Point to banner: Gemini mode, cost-controlled.*

## Scan and analyze (20s)

> "I'll upload a product photo — here a synthetic demo label — and tap Analyze."

*Upload image → Analyze image → wait for result.*

> "Gemini reads the packaging and returns product name, category, insights, warnings, and suggested follow-up questions. When Open Food Facts matches, you see citations — grounding status is always visible."

*Scroll result card: AI Analysis badge, grounding, insights.*

## Insights (10s)

> "The latest analysis persists locally on device as JSON only — no images stored."

*Navigate to Insights → show latest analysis.*

## Compare (15s)

> "Compare loads Product A from your latest scan. Product B can come from another analysis or history. Compare sends analysis JSON only — no image bytes."

*Open Compare → show side-by-side diff.*

## Activity and guardrails (15s)

> "Activity shows your local scan log plus backend metrics and usage limits — five analyses per session, daily cost cap, cache stats. This keeps the public demo sustainable."

*Open Activity → metrics and limits.*

## Gemini Live (10s)

> "Gemini Live adds voice and vision — it's ready but access-code gated, with a 60-second session cap. We're showing the gated UI, not exposing credentials."

*Scroll to Live panel on scan or show mobile screenshot.*

## Close (10s)

> "SnapInsight is a full workflow: vision, grounding, compare, graph, metrics, and privacy guardrails — deployed on Vercel and Render with real Gemini, not a mock-only demo. It's an assistant for product understanding, not medical or regulatory advice."

---

**Total:** ~90 seconds  
**Backup:** If backend is cold, note banner "Backend waking up" and retry after a few seconds.
