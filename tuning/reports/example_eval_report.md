# Example Eval Report (template)

This is an **illustrative template** showing the shape of the report produced by
`tuning/src/evaluate.py` and the kind of results to expect. The numbers in the
"Illustrative expectation" column are **not measured** — they are reasonable
targets for a small LoRA run on `google/flan-t5-small` with the seed dataset.
Real numbers depend on the base model, hyperparameters, and run-to-run variance.

**No real training run has been performed in this repository.** No tuned adapter
is committed, so no real metrics exist yet — the tables below are illustrative
targets and a CPU mock-logic reference, not measured model results.

A real report is generated, after training, with:

```bash
# Honest held-out evaluation (train on --split train, evaluate on --split eval):
python3 tuning/src/evaluate.py \
    --model tuning/outputs/ \
    --data tuning/data/product_intelligence_seed.jsonl \
    --split eval \
    --report tuning/reports/eval_report.md
```

`tuning/reports/eval_report.md` (the real output) is gitignored. Only this
example template is committed.

## Recommended provenance fields for a real eval report

A credible real report should record enough to reproduce it. `evaluate.py`
auto-emits a "Run metadata" header (generated-at timestamp, dataset, eval split,
model label). When you publish results, also capture:

- **Model name / adapter path** and **base model** (e.g. `google/flan-t5-small`).
- **Dataset name + version** (see `tuning/data/DATASET_CARD.md`).
- **Train/eval split** used (e.g. `--split train` / `--split eval`, holdout frac, seed).
- **Hardware** (e.g. Colab T4) and **approximate runtime**.
- **Hyperparameters** (epochs, LR, LoRA r/alpha) — saved to
  `tuning/outputs/train_config.json` by `train_lora.py`.
- **Metrics** (the table below) and **known failure cases / qualitative notes**.

---

## Metrics explained

| Metric | What it measures | Target |
|---|---|---|
| **Valid JSON rate** | Fraction of generations parseable as JSON | High (→100%) |
| **Required fields present** | Fraction passing the full canonical schema (`schemas.py`) | High (→100%) |
| **Category accuracy** | `normalized_category` matches the reference (where a label exists) | Higher is better |
| **Caution-level accuracy** | `caution_level` matches the reference enum | Higher is better |
| **Warning-label F1** | Set precision/recall/F1 of `warning_labels` (partial match) | Higher is better |
| **Exact structured match** | Whole output object equals the reference exactly | Hard; low is normal |
| **Partial field match** | Average per-field agreement across all 8 fields | Higher is better |
| **Medical-claim violations** | Generated `safe_summary` containing banned medical/health phrasing | **0** (hard requirement) |

## Illustrative expectation: baseline vs tuned (flan-t5-small)

| Metric | Untuned baseline | After small LoRA | Illustrative expectation |
|---|---|---|---|
| Valid JSON rate | low–moderate | near 100% | tuning teaches the strict JSON shape |
| Required fields present | low | near 100% | all 8 keys emitted reliably |
| Category accuracy | moderate | improved | normalization learned from labels |
| Caution-level accuracy | low | improved | calibrated to the dataset rubric |
| Warning-label F1 | low–moderate | improved | allergen/additive patterns learned |
| Exact structured match | ~0% | modest | exact match is intentionally strict |
| Partial field match | low | high | most fields broadly correct |
| Medical-claim violations | may be > 0 | **0** | safety constraint must hold |

> The single most important result is **0 medical-claim violations** in the
> tuned model's `safe_summary` outputs. A tuned model that scores well but emits
> medical claims is a FAILED run for this task.

## CPU mock reference (no model) — validates the evaluator, not the model

Running `evaluate.py --mock` (used by smoke tests and CI) does not load a model.
**It validates the evaluator, not actual model performance.** It scores
deterministic "baseline" vs "tuned" mock predictions purely to exercise the
metric logic. A representative mock run on the 45-example seed dataset shows the
eval logic cleanly separating the two:

| Metric | baseline (mock) | tuned (mock) |
|---|---|---|
| Valid JSON rate | ~58% | 100% |
| Required fields present | ~29% | 100% |
| Caution-level accuracy | ~8% | 100% |
| Warning-label F1 | ~35% | 100% |
| Exact structured match | 0% | ~80% |
| Medical-claim violations | 13 | 0 |

These mock figures only demonstrate that the metrics distinguish good from bad
structured output; they are **not** a claim about any trained model.
