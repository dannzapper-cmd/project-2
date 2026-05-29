# SnapInsight — Cost, Privacy, and Safety

> **Status:** Policies and controls described here are **planned**. Block 0 establishes principles; implementation lands in later blocks.

## Cost controls (planned)

### Tier strategy

- **Target:** Operate within free or low-cost tiers during development and early demo, using official provider documentation as the source of truth for quotas and pricing.
- **Research note to verify:** Gemini, Supabase, Modal, Vercel, and Langfuse publish tier limits on their pricing pages—confirm current RPM/TPM, storage, and egress before each block. Do not treat secondary summaries as canonical.

### Planned mechanisms

| Control | Purpose | Target block |
|---------|---------|--------------|
| Perceptual hash cache | Avoid duplicate multimodal calls for similar images | Block 11 |
| Model routing | Flash-Lite default; stronger model on retry / low confidence | Blocks 4, 11 |
| Request rate limits | Protect API keys and quotas | Blocks 3, 11 |
| Session / daily caps | Prevent runaway spend in demos | Block 11 |
| Retry with backoff | Handle transient provider errors without storms | Block 3+ |
| Structured output | Smaller, parseable responses; fewer repair calls | Block 4 |

### Cost documentation rules

- Do not publish hard cost guarantees in user-facing copy.
- Use **estimated** language tied to named official sources when discussing tiers.
- In-app metrics (future) should show **relative** or **session** cost indicators where exact billing is unavailable.

## Privacy (planned)

### Images

- **Strip EXIF** metadata on client or server before any storage or model call (future block).
- **Ephemeral processing:** analyze and discard; persist only perceptual hash or derived features for cache—not raw photos by default.
- **No unnecessary retention:** debug image retention requires explicit dev flag and short TTL.

### Data collection

- **No PII by default:** no account required for demo; no email harvesting in v1.
- **Minimal logs:** request IDs, hashes, latency, model ID—not image bytes in production logs.

### Secrets

- **API keys server-side only** (FastAPI / backend host).
- Never commit secrets; use environment variables and platform secret stores at deploy time.

### Consent (planned UI)

- Clear notice before camera use: image used for this analysis session.
- Link to privacy policy before any data retention feature ships.

## Safety (planned)

### Content boundaries

| Rule | Implementation direction |
|------|---------------------------|
| No medical diagnosis | System prompts + output filters + UI disclaimers |
| No absolute health claims | Copy review + model instructions |
| No counterfeit / authenticity claims | Block product copy and model outputs in this category |
| Cite data sources | Source cards for Open Food Facts and other datasets |
| Show uncertainty | Confidence UI, possible matches, fallback to cited RAG-only facts |
| Graceful fallback | When model or RAG fails, explain limits and suggest retake or manual search |

### Allergens and nutrition

- Present allergen and ingredient data as **sourced from datasets or model interpretation of the image**, with “verify on package” messaging.
- Never state that the app is safe for a specific individual’s allergies without explicit user-owned confirmation flows (future: user preference only as hints, not guarantees).

### Prompt and eval safety

- Maintain a **safety prompt appendix** in backend config (future block).
- Golden-set tests for refused categories: diagnosis, counterfeit, absolute health (Block 14).

## Open Food Facts attribution (planned)

UI will include attribution consistent with Open Food Facts terms, e.g. data under Open Database License with link to the product record. Exact strings will match [official terms](https://world.openfoodfacts.org/terms-of-use) at implementation time.

## Provider-specific notes (verify before build)

The following are **strategic options** from initial research—not committed contracts:

| Provider | Role | Verify at |
|----------|------|-----------|
| Google Gemini | Multimodal inference | https://ai.google.dev/gemini-api/docs/pricing |
| Open Food Facts | Primary RAG source | https://world.openfoodfacts.org/data |
| Supabase | Optional Postgres + pgvector | https://supabase.com/pricing |
| Modal | Optional FastAPI hosting | https://modal.com/pricing |
| Vercel | PWA hosting | https://vercel.com/pricing |
| Langfuse | Observability | https://langfuse.com/pricing |

Alternatives (Render, Railway, Fly, Neon, Cloudflare R2) remain valid if quotas or terms change.

## Competitive safety positioning

SnapInsight will not claim superiority over Yuka, Google Lens, or others without evidence. Differentiation is **transparent citations, confidence UX, and multimodal camera-first flow**—not unverifiable accuracy percentages.
