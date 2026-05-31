# Run the SnapInsight 18C tuning pipeline on Google Colab

This is a clean, copy-paste guide for running a real small LoRA tuning job on a
free **Colab T4 GPU**. It is a Markdown guide rather than a committed `.ipynb`
because we cannot verify notebook outputs here, and an honest, reproducible set
of commands is more trustworthy than a notebook with stale/fabricated cell
output.

> ⚠️ **`tuning/outputs/` is gitignored. Download your eval report before closing
> the Colab session.** Colab runtimes are ephemeral — adapters, checkpoints, and
> reports are lost when the session ends unless you download them.

No API keys or secrets are required. No Google API is called. No paid services.

---

## Steps (run in order)

### 1. Open a Colab GPU runtime

In Colab: **Runtime → Change runtime type → Hardware accelerator → T4 GPU**.
The free T4 tier is sufficient for `google/flan-t5-small`.

Confirm the GPU is visible:

```python
!nvidia-smi
```

### 2. Clone the repo

```bash
!git clone https://github.com/<your-org-or-user>/<your-repo>.git
%cd <your-repo>
```

Replace the URL with this repository's clone URL. If you are tuning a feature
branch, check it out: `!git checkout feature/18c-small-product-tuning-pipeline`.

### 3. Install the tuning dependencies

```bash
!pip install -r tuning/requirements.txt
```

This installs `torch`, `transformers`, `peft`, `datasets`, `accelerate`, and
`sentencepiece` (needed by the flan-t5 tokenizer). It does **not** touch the
backend or frontend dependencies.

### 4. Validate the dataset (fast, CPU)

```bash
!python3 tuning/src/validate_dataset.py tuning/data/product_intelligence_seed.jsonl
```

Expect `PASS: dataset is valid against the canonical schema.` Fix any reported
errors before training.

### 5. Train a small LoRA adapter (GPU)

```bash
!python3 tuning/src/train_lora.py \
    --model google/flan-t5-small \
    --data tuning/data/product_intelligence_seed.jsonl \
    --output tuning/outputs/
```

This downloads the small base model, attaches a LoRA adapter, trains for a few
epochs on the seed dataset, and saves the adapter + tokenizer under
`tuning/outputs/`. With ~45 examples on a T4 this is quick. Tune
`--epochs`, `--learning-rate`, `--lora-r` as needed.

> To try the stronger alternative, swap in `--model Qwen/Qwen2.5-0.5B`. It is a
> decoder-only causal model (~500M params, Apache 2.0); the script detects the
> architecture automatically.

### 6. Evaluate baseline-vs-tuned and write a report

```bash
!python3 tuning/src/evaluate.py \
    --model tuning/outputs/ \
    --data tuning/data/product_intelligence_seed.jsonl \
    --report tuning/reports/eval_report.md
```

This loads your adapter, generates structured predictions, scores them against
the canonical schema, and writes a Markdown report. The most important line is
**Medical-claim violations** — it must be **0**.

You can also run the no-model mock eval to sanity-check the metric logic:

```bash
!python3 tuning/src/evaluate.py --mock --data tuning/data/product_intelligence_seed.jsonl
```

### 7. Download your report (do NOT commit outputs)

```python
from google.colab import files
files.download("tuning/reports/eval_report.md")
```

> **Do NOT commit `tuning/outputs/` or model weights/adapters/checkpoints.** They
> are gitignored on purpose. Only the eval report is worth keeping, and you
> download it locally rather than pushing it.

---

## Optional: export the dataset for a later Vertex AI tuning path

```bash
!python3 tuning/src/build_vertex_sft_jsonl.py \
    --data tuning/data/product_intelligence_seed.jsonl \
    --output tuning/outputs/vertex_sft.jsonl
```

This writes a local `{"input_text": ..., "output_text": ...}` JSONL in the
Vertex AI Supervised Tuning format. It does not call Google. The file lives under
the gitignored `tuning/outputs/` directory.

## Troubleshooting

- **Out of memory:** reduce `--batch-size` (e.g. to `2`) or `--max-input-tokens`.
- **Tokenizer error for flan-t5:** ensure `sentencepiece` installed (it is in
  `requirements.txt`).
- **CPU-only runtime:** training will be very slow; switch to a T4 GPU runtime.
