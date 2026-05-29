# SnapInsight — Limitations

Honest limitations are part of the product design—not bugs to hide. This document states what SnapInsight is **not** and what users should expect.

## Product scope

- SnapInsight is an **informational companion** for packaged products, not a medical device or clinical tool.
- Nutrition, allergen, and ingredient information is **informational**. Users must verify against the physical product label and consult qualified professionals for health decisions.
- The product is under active development; capabilities described in docs are **planned** unless a release note states otherwise.

## Identification and data quality

- **No guaranteed product identification.** Visual similarity, poor lighting, obscure brands, and incomplete datasets can produce wrong or partial matches.
- **Open Food Facts and curated data can be incomplete or wrong** in some regions and categories. Citations show provenance; they do not guarantee correctness.
- **Confidence and fallback UX** (possible matches, retake photo, manual confirm) are intentional—not optional polish.

## Explicit non-capabilities

| Area | Limitation |
|------|------------|
| Medical | No diagnosis, treatment, or personalized medical advice. |
| Health claims | No absolute claims (“safe for everyone”, “cures”, guaranteed outcomes). |
| Counterfeits | No authenticity or counterfeit detection. |
| Pricing | No real-time price scraping or purchase guarantees. |
| Legal compliance | Does not replace regulatory label review for manufacturers. |

## Model and AI limitations

- Multimodal models can **hallucinate** fields not visible on the package.
- RAG reduces but does not eliminate hallucination; retrieval misses still occur.
- Structured JSON output can be **confidently wrong**; UI must surface uncertainty.
- Free or low-cost API tiers have **quotas**; aggressive caching and graceful degradation are required (see [cost-privacy-safety.md](./cost-privacy-safety.md)).

## Privacy and images

- Images should be treated as **ephemeral** by default: processed for analysis, not retained for profiling.
- Long-term storage of user photos is out of scope unless explicitly opted in for a defined feature (e.g. saved history in a future version—with clear policy).

## Deferred features

The following are **not** promised in early releases:

- Full **live camera streaming** (WebRTC-heavy “always-on vision”).
- **GraphRAG** across large knowledge graphs.
- **Advanced voice** (custom wake word, offline STT).
- **Local fine-tuning** as the primary intelligence layer.

These may be explored in later blocks only if the core capture → analyze → cite → chat path is stable.

## Operational limitations

- Demo and early deployments may run on **hobby-tier** hosting with pause-on-limit behavior—verify provider terms before commercial use.
- Observability in early blocks may be **developer-facing** only, not a full SLA-backed monitoring product.

## User-facing copy (planned)

Disclaimers will appear in the app, including variants of:

- “This is not medical advice. Consult a healthcare professional for health decisions.”
- “Ingredient and allergen data may come from Open Food Facts. Always check the product label.”
- “We may not identify this product correctly. Confirm before relying on this information.”

Exact wording will be finalized with legal review before any public commercial launch.
