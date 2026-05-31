# SnapInsight — Small Product Intelligence Tuning Pipeline (Block 18C)

A real, reproducible **LoRA tuning pipeline** that adapts a small open model for
SnapInsight-style **product intelligence** tasks. It is an additional technical
capability and experiment — **not** a replacement for SnapInsight's Gemini
multimodal runtime.

The tuned task is **text / metadata based, not multimodal**. Given structured
product metadata, the model produces a structured JSON response useful for
SnapInsight.

- **Input:** product name, brand, category, ingredients, nutrition facts,
  OpenFoodFacts-style fields, and existing warnings / citations / grounding
  status when available.
- **Output:** a structured JSON object (see [Output schema](#output-schema)) with
  a normalized category, likely product attributes, nutrition/warning flags,
  evidence-aware caution labels, suggested next questions, a safe summary, and a
  medical-claim flag. **No medical claims.**

## What 18C does

- Defines a single canonical output schema (`src/schemas.py`) used everywhere.
- Ships a small, credible seed dataset (`data/product_intelligence_seed.jsonl`,
  v0.1.0, 45 examples; see [`data/DATASET_CARD.md`](./data/DATASET_CARD.md)) of
  **fictional/generic** CPG/food products with easy, ambiguous, missing-data, and
  "do-not-overclaim" cases.
- Validates the dataset on CPU in well under 10 seconds (`src/validate_dataset.py`).
- Trains a real LoRA adapter on a small open model (`src/train_lora.py`),
  supporting both encoder-decoder (flan-t5) and decoder-only (Qwen) models.
- Evaluates baseline vs tuned with structured metrics, including a CPU
  `--mock` mode (`src/evaluate.py`).
- Exports the same data to a Vertex AI Supervised Tuning JSONL
  (`src/build_vertex_sft_jsonl.py`) **without** calling Google or adding
  google-cloud dependencies.
- Includes CPU smoke tests (`tests/test_dataset_validation.py`).

## Why Gemini for runtime but a tuning pipeline here?

SnapInsight's product experience is **multimodal** (a user shows a photo of a
package). Gemini handles that vision+text reasoning at runtime and remains the
main product engine. Open-model fine-tuning is not a good fit for the multimodal
runtime path, and (see honesty note below) the Gemini API does not offer direct
fine-tuning.

This pipeline instead specializes a small model on the **text/metadata**
sub-problem: turning already-extracted product fields into a consistent,
schema-valid, safety-constrained structured response. That is a credible place
for a small tuned model to add value (consistency, strict JSON, calibrated
caution) and a credible way to demonstrate fine-tuning capability without
overbuilding enterprise infrastructure.

## Output schema

Defined once in `src/schemas.py`. Both `train_lora.py` and `evaluate.py` import
and validate against it.

```json
{
  "normalized_category": "string",
  "product_attributes": ["string"],
  "nutrition_flags": ["string"],
  "warning_labels": ["string"],
  "caution_level": "none | low | medium | high",
  "suggested_questions": ["string"],
  "safe_summary": "string",
  "medical_claim_detected": true
}
```

`medical_claim_detected` means the **source metadata** (e.g. on-package marketing
copy) contained a medical/absolute-health claim that must not be propagated.
When true, `safe_summary` still stays neutral and does not repeat the claim.

## Layout

```
tuning/
├── README.md                         # this file
├── COLAB.md                          # step-by-step Colab GPU guide
├── requirements.txt                  # isolated tuning deps (not app deps)
├── data/
│   ├── product_intelligence_seed.jsonl
│   └── DATASET_CARD.md               # version, provenance, composition, limits
├── src/
│   ├── schemas.py                    # canonical schema + prompt builder
│   ├── validate_dataset.py           # CPU dataset validation
│   ├── train_lora.py                 # real PEFT/LoRA training (+ --smoke-test)
│   ├── evaluate.py                   # baseline vs tuned eval (+ --mock)
│   └── build_vertex_sft_jsonl.py     # Vertex AI SFT JSONL exporter
├── reports/
│   └── example_eval_report.md        # report template (real reports gitignored)
├── tests/
│   └── test_dataset_validation.py    # CPU smoke tests
└── outputs/                          # gitignored: adapters, checkpoints, exports
```

## Recommended base models

All recommended models are **Apache 2.0** licensed. Do **not** default to any
model larger than 1B params.

| Model | License | Size | Notes |
|---|---|---|---|
| `google/flan-t5-small` (**default**) | **Apache 2.0** | ~60M | Encoder-decoder. Runs on CPU for smoke tests; trains on Colab free T4. |
| `google/flan-t5-base` | **Apache 2.0** | ~250M | Encoder-decoder. Better quality, still T4-friendly. |
| `Qwen/Qwen2.5-0.5B` | **Apache 2.0** | ~500M | Decoder-only causal. Stronger instruction following. |

The base model is configurable via `--model`, the `SNAPINSIGHT_TUNE_MODEL`
environment variable, or by editing the default in `train_lora.py`. The script
auto-detects encoder-decoder vs causal architecture.

## How to run

The pipeline has three distinct phases, intentionally kept separate:

1. **Smoke test** (CPU, no model, no GPU) — validate data + config + metric logic.
2. **Actual training** (GPU) — produce a LoRA adapter under `tuning/outputs/`.
3. **Actual evaluation** (GPU) — score the trained adapter and write a report.

### 1. Validate the dataset (CPU, no model download, < 10s)

```bash
python3 tuning/src/validate_dataset.py tuning/data/product_intelligence_seed.jsonl
```

### 2. Smoke-test the training config (CPU, no model download)

```bash
python3 tuning/src/train_lora.py --smoke-test
```

### 3. Run the CPU smoke tests

```bash
python3 -m pytest tuning/tests -v
```

### 4. Train a real LoRA adapter (requires a GPU runtime)

Install deps first (ideally in a fresh venv or on Colab/Kaggle/RunPod):

```bash
pip install -r tuning/requirements.txt

# Train on the held-out TRAIN split so eval is honest (recommended):
python3 tuning/src/train_lora.py \
    --model google/flan-t5-small \
    --data tuning/data/product_intelligence_seed.jsonl \
    --split train \
    --output tuning/outputs/
```

On a free Colab **T4 GPU**, `flan-t5-small` LoRA on this ~45-example dataset is a
matter of minutes (small model, tiny dataset, a handful of epochs). `flan-t5-base`
and `Qwen2.5-0.5B` take longer but remain T4-feasible.

**Artifacts produced** (under `tuning/outputs/`, all gitignored — do NOT commit):

- `adapter_model.safetensors` + `adapter_config.json` — the LoRA adapter.
- tokenizer files (`tokenizer*.json`, `special_tokens_map.json`, etc.).
- `train_config.json` — the exact run config (model, split, hyperparameters).

No base-model weights are committed; the adapter references the base model by id.

### 5. Evaluate baseline vs tuned

```bash
# 5a. No-model mock eval (CPU) — validates the EVALUATOR, not model quality:
python3 tuning/src/evaluate.py --mock --data tuning/data/product_intelligence_seed.jsonl

# 5b. Real-model eval on the HELD-OUT eval split (GPU) — writes a Markdown report:
python3 tuning/src/evaluate.py \
    --model tuning/outputs/ \
    --data tuning/data/product_intelligence_seed.jsonl \
    --split eval \
    --report tuning/reports/eval_report.md
```

> **In-sample vs held-out:** `--split all` (the default) evaluates on the same
> records used for training and therefore measures schema adherence / consistency,
> not generalization. Use `--split train` for training and `--split eval` for an
> honest held-out signal. The split is reproducible (content hash, seed 42,
> default 20% holdout → train=37 / eval=8 for v0.1.0).
>
> The `--mock` run loads no model; it only proves the metric logic separates good
> from bad structured output. It is **not** a claim about any trained model.

### 6. Export to Vertex AI SFT JSONL (optional, no Google API)

```bash
python3 tuning/src/build_vertex_sft_jsonl.py \
    --data tuning/data/product_intelligence_seed.jsonl \
    --output tuning/outputs/vertex_sft.jsonl
```

Output format (one object per line), matching the Vertex AI Supervised Tuning
spec: `{"input_text": "<prompt>", "output_text": "<json_response>"}`.

## Run on Colab

For a free-tier **T4 GPU** walkthrough (clone → install → validate → train →
evaluate → download report), see **[COLAB.md](./COLAB.md)**. No API keys needed.

## Recommended low-cost execution options

- **Local CPU:** validation and smoke tests only (`validate_dataset.py`,
  `train_lora.py --smoke-test`, `pytest`, `evaluate.py --mock`). Do **not** run
  real training on CPU.
- **Colab / Kaggle free GPU (T4):** sufficient for `flan-t5-small` LoRA training
  on this small dataset. See [COLAB.md](./COLAB.md).
- **RunPod / other rented GPU:** for `Qwen2.5-0.5B` or `flan-t5-base` and larger
  experiments.

## Metrics

`evaluate.py` reports: valid JSON rate, required-fields-present rate,
normalized-category accuracy (where labels exist), caution-level accuracy,
warning-label F1 (set partial match), medical-claim violation count, and
exact/partial structured match. See
[reports/example_eval_report.md](./reports/example_eval_report.md) for the report
format and illustrative expectations. The hard requirement is **0 medical-claim
violations** in generated summaries.

## What this pipeline does NOT do

- It does **not** replace Gemini multimodal runtime in SnapInsight. Gemini
  remains the main product engine.
- It does **not** include trained model weights, adapters, or checkpoints. They
  are gitignored (see [.gitignore](../.gitignore) and `outputs/`).
- Training **requires an external GPU runtime** (Colab/Kaggle/RunPod). See
  [COLAB.md](./COLAB.md). CPU is for validation and smoke tests only.
- Results are **not** validated on production SnapInsight data; the seed dataset
  is small and uses fictional/generic products.
- Google AI Studio / the Gemini API **does not support direct fine-tuning** as of
  May 2026. This pipeline therefore tunes a separate small **open** model and is
  not "Gemini fine-tuning".
- It is **not** integrated into the production UI, backend runtime, or any
  scan/chat/compare/session/graph behavior. No auth, storage, uploads, user
  history, or paid API calls are added.

## Future: Gemini as Distillation Teacher

> **TODO (not implemented; not a claim).** A future iteration could use the
> Gemini API as a *distillation teacher*: feed unlabeled product metadata to
> Gemini to generate high-quality synthetic `output` labels in this exact schema,
> producing a larger and higher-quality training set for the small student model.
> This would be gated behind explicit configuration and quota, would keep all API
> calls server-side, and would still avoid committing model weights. It is listed
> here as a direction only and is intentionally **not** built in 18C.

## Safety and privacy

- No private user data; products are fictional/generic.
- No real copyrighted product labels copied verbatim.
- No secrets, credentials, or `.env` values.
- The schema and validator forbid medical/absolute-health claims in generated
  summaries; this is enforced in tests.
