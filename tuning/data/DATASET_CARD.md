# Dataset Card — `product_intelligence_seed`

| Field | Value |
|---|---|
| **Name** | `product_intelligence_seed` |
| **Version** | `0.1.0` (seed / starter) |
| **File** | `tuning/data/product_intelligence_seed.jsonl` |
| **Records** | 45 |
| **Task** | Structured product-intelligence generation (text/metadata → JSON) |
| **Schema** | `tuning/src/schemas.py` (canonical, single source of truth) |
| **License of content** | Original, hand-authored for this repo |

## What this is

A small, hand-authored **seed** dataset for the SnapInsight Block 18C tuning
pipeline. Each record maps structured product metadata (`input`) to a
schema-valid structured response (`output`). It is intended to **bootstrap a
first small LoRA experiment**, not to be a benchmark.

## Provenance & privacy

- **Fictional / generic products only.** Brand and product names are invented
  (e.g. "Meadowfield", "Brightwell"). Any resemblance to real products is
  coincidental.
- **No private or user data.** Nothing is sourced from real SnapInsight usage.
- **No copyrighted labels copied verbatim.** Nutrition values are plausible,
  illustrative figures, not transcriptions of real packaging.
- **No medical or absolute-health claims** in labels (enforced by
  `validate_dataset.py` and the tests).

## Record format

```json
{
  "id": "seed-001",
  "difficulty": "easy | ambiguous | missing | overclaim",
  "split": "(optional) train | eval — pins a record to a split",
  "input": { "product_name": "...", "brand": "...", "category": "...",
             "ingredients": [...], "nutrition": {...}, "off_fields": {...},
             "grounding_status": "...", "warnings": [...], "citations": [...] },
  "output": { /* canonical schema, see schemas.py */ }
}
```

`split` is optional. If absent, a record's split is assigned by the reproducible
content hash in `deterministic_split` (default 20% holdout, seed 42).

## Composition (v0.1.0)

| Difficulty bucket | Count | Purpose |
|---|---|---|
| `easy` | 19 | clear category, full grounded data |
| `ambiguous` | 9 | unclear category / partial match / dry-vs-prepared ambiguity |
| `missing` | 9 | partial or absent nutrition / ingredients / brand |
| `overclaim` | 8 | on-package health/marketing claims that must NOT be propagated |

The set deliberately includes partial/missing nutrition, ambiguous categories,
additives/allergen warnings, low-confidence (`no_match` / `grounding_unavailable`)
cases, and "do-not-overclaim" cases. 8 records set `medical_claim_detected: true`
(source had a health claim) while keeping `safe_summary` neutral.

## Reproducible split

- Default: `deterministic_split(..., split="train"|"eval", holdout_frac=0.2, seed=42)`.
- v0.1.0 default holdout: **train=37, eval=8**, with the eval set spanning all
  four difficulty buckets.
- `--split all` (the script default) uses every record; that is **in-sample** and
  measures consistency, not generalization.

## Intended use & limitations

- **Use:** smoke-validate the pipeline and run a first small LoRA experiment.
- **Not for:** production claims, medical guidance, or benchmark comparisons.
- 45 examples is enough to demonstrate the pipeline and observe schema-adherence
  gains; it is **too small** to claim general product-intelligence quality. Scale
  up (and/or use the README's distillation-teacher TODO) before any such claim.

## Changelog

- **0.1.0** — initial 45-example seed set (easy/ambiguous/missing/overclaim).
