#!/usr/bin/env python3
"""Real PEFT/LoRA fine-tuning for the SnapInsight product-intelligence task.

This script adapts a SMALL open instruction model (default
``google/flan-t5-small``, Apache 2.0) on the structured product-intelligence
dataset using LoRA. It supports both encoder-decoder models (T5 family) and
decoder-only causal models (e.g. ``Qwen/Qwen2.5-0.5B``) and chooses the right
training setup automatically.

GPU is required for real training. A ``--smoke-test`` flag validates the config
and dataset on CPU WITHOUT downloading any model or running training, so this
script is safe to exercise in CI / app builds.

Heavy ML dependencies (torch, transformers, peft, datasets) are imported lazily
inside the training path so that ``--smoke-test`` and ``--help`` work without
them installed.

Example (GPU runtime, e.g. Colab T4):

    python3 tuning/src/train_lora.py \\
        --model google/flan-t5-small \\
        --data tuning/data/product_intelligence_seed.jsonl \\
        --output tuning/outputs/

Outputs (adapter weights, tokenizer, training args) are written under
``tuning/outputs/`` which is gitignored. Do NOT commit them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import build_prompt, render_output_json  # noqa: E402
from validate_dataset import (  # noqa: E402
    DEFAULT_HOLDOUT_FRAC,
    SPLIT_CHOICES,
    deterministic_split,
    load_jsonl,
    validate_dataset,
)

DEFAULT_MODEL = os.environ.get("SNAPINSIGHT_TUNE_MODEL", "google/flan-t5-small")
DEFAULT_DATA = str(
    Path(__file__).resolve().parents[1] / "data" / "product_intelligence_seed.jsonl"
)
DEFAULT_OUTPUT = str(Path(__file__).resolve().parents[1] / "outputs")

GPU_BANNER = (
    "This script requires a GPU runtime (Colab/Kaggle/RunPod).\n"
    "For smoke test only, use --smoke-test flag which skips actual training\n"
    "and validates config only."
)

# Models we have documented as safe small defaults (Apache 2.0 / MIT). Used only
# for a friendly warning, never to block an explicit user choice.
RECOMMENDED_MODELS = {
    "google/flan-t5-small": "Apache 2.0, ~60M params, CPU-friendly smoke, T4 training",
    "google/flan-t5-base": "Apache 2.0, ~250M params, T4 training",
    "Qwen/Qwen2.5-0.5B": "Apache 2.0, ~500M params, better instruction following",
}


@dataclass
class TrainConfig:
    model: str
    data: str
    output: str
    split: str
    holdout_frac: float
    epochs: int
    learning_rate: float
    batch_size: int
    grad_accum: int
    max_input_tokens: int
    max_target_tokens: int
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    seed: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LoRA fine-tune a small open model for SnapInsight product intelligence.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF model id or local path.")
    parser.add_argument("--data", default=DEFAULT_DATA, help="JSONL training dataset.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output dir for the adapter.")
    parser.add_argument(
        "--split",
        choices=SPLIT_CHOICES,
        default="all",
        help="Which reproducible subset to train on. Use 'train' to hold out an eval set.",
    )
    parser.add_argument(
        "--holdout-frac",
        type=float,
        default=DEFAULT_HOLDOUT_FRAC,
        help="Fraction of records assigned to the eval holdout when --split is used.",
    )
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--grad-accum", type=int, default=2)
    parser.add_argument("--max-input-tokens", type=int, default=512)
    parser.add_argument("--max-target-tokens", type=int, default=320)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Validate config + dataset on CPU without downloading a model or training.",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> TrainConfig:
    return TrainConfig(
        model=args.model,
        data=args.data,
        output=args.output,
        split=args.split,
        holdout_frac=args.holdout_frac,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        max_input_tokens=args.max_input_tokens,
        max_target_tokens=args.max_target_tokens,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        seed=args.seed,
    )


def build_examples(
    data_path: str,
    *,
    split: str = "all",
    holdout_frac: float = DEFAULT_HOLDOUT_FRAC,
) -> list[dict[str, str]]:
    """Load the dataset and return prompt/target pairs using the shared schema."""

    records = deterministic_split(
        load_jsonl(data_path), split=split, holdout_frac=holdout_frac
    )
    examples: list[dict[str, str]] = []
    for record in records:
        record_input = record.get("input") or {}
        record_output = record.get("output") or {}
        examples.append(
            {
                "prompt": build_prompt(record_input),
                "target": render_output_json(record_output),
            }
        )
    return examples


def validate_config(config: TrainConfig) -> list[str]:
    """Lightweight config sanity checks. Returns a list of problems (empty = ok)."""

    problems: list[str] = []
    if config.epochs <= 0:
        problems.append("epochs must be > 0")
    if config.learning_rate <= 0:
        problems.append("learning_rate must be > 0")
    if config.batch_size <= 0:
        problems.append("batch_size must be > 0")
    if config.lora_r <= 0:
        problems.append("lora_r must be > 0")
    if config.max_input_tokens <= 0 or config.max_target_tokens <= 0:
        problems.append("token limits must be > 0")
    if not Path(config.data).exists():
        problems.append(f"dataset not found: {config.data}")
    return problems


def run_smoke_test(config: TrainConfig) -> int:
    """CPU-only path: validate config + dataset, build prompt/target pairs.

    No model download, no torch import, no training. Designed to be fast and
    safe for CI and app builds.
    """

    print("[smoke-test] Validating training config and dataset (no model download)...")
    print(config.to_json())

    problems = validate_config(config)
    if problems:
        print("[smoke-test] FAIL: config problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    report = validate_dataset(config.data)
    if not report.ok:
        print(f"[smoke-test] FAIL: dataset invalid ({len(report.errors)} error(s)):")
        for err in report.errors[:10]:
            print(f"  - {err}")
        return 1

    examples = build_examples(config.data, split=config.split, holdout_frac=config.holdout_frac)
    if not examples:
        print("[smoke-test] FAIL: no training examples were built.")
        return 1
    print(f"[smoke-test] Split='{config.split}' selected {len(examples)} record(s) for training.")

    sample = examples[0]
    print(f"[smoke-test] Built {len(examples)} prompt/target pairs.")
    print("[smoke-test] Example prompt (truncated):")
    print("  " + sample["prompt"][:200].replace("\n", "\n  "))
    print("[smoke-test] Example target (truncated):")
    print("  " + sample["target"][:200])

    if config.model not in RECOMMENDED_MODELS:
        print(
            f"[smoke-test] NOTE: '{config.model}' is not in the recommended small-model "
            "list. Ensure it is <=1B params and Apache 2.0/MIT licensed."
        )
    print("[smoke-test] PASS: config and dataset are ready for GPU training.")
    return 0


def run_training(config: TrainConfig) -> int:
    """Real LoRA training. Requires torch/transformers/peft/datasets and a GPU."""

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (
            AutoConfig,
            AutoModelForCausalLM,
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
            DataCollatorForLanguageModeling,
            DataCollatorForSeq2Seq,
            Trainer,
            TrainingArguments,
            set_seed,
        )
    except ImportError as exc:  # pragma: no cover - depends on optional deps
        print("ERROR: training dependencies are not installed.")
        print(f"  ({exc})")
        print("Install them with: pip install -r tuning/requirements.txt")
        print("Then run on a GPU runtime, or use --smoke-test on CPU.")
        return 1

    set_seed(config.seed)

    if not torch.cuda.is_available():  # pragma: no cover - environment dependent
        print("WARNING: no CUDA GPU detected. Training on CPU will be extremely slow.")
        print("Use a Colab/Kaggle/RunPod GPU runtime for real training.")

    examples = build_examples(config.data, split=config.split, holdout_frac=config.holdout_frac)
    print(f"Loaded {len(examples)} examples from {config.data} (split='{config.split}')")

    hf_config = AutoConfig.from_pretrained(config.model)
    is_encoder_decoder = bool(getattr(hf_config, "is_encoder_decoder", False))
    tokenizer = AutoTokenizer.from_pretrained(config.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if is_encoder_decoder:
        base_model = AutoModelForSeq2SeqLM.from_pretrained(config.model)
        task_type = TaskType.SEQ_2_SEQ_LM
    else:
        base_model = AutoModelForCausalLM.from_pretrained(config.model)
        task_type = TaskType.CAUSAL_LM

    lora_config = LoraConfig(
        task_type=task_type,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias="none",
    )
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    def tokenize_seq2seq(batch: dict) -> dict:
        model_inputs = tokenizer(
            batch["prompt"],
            max_length=config.max_input_tokens,
            truncation=True,
        )
        labels = tokenizer(
            text_target=batch["target"],
            max_length=config.max_target_tokens,
            truncation=True,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    def tokenize_causal(batch: dict) -> dict:
        texts = [
            f"{prompt}\n{target}{tokenizer.eos_token}"
            for prompt, target in zip(batch["prompt"], batch["target"])
        ]
        tokenized = tokenizer(
            texts,
            max_length=config.max_input_tokens + config.max_target_tokens,
            truncation=True,
        )
        tokenized["labels"] = [ids.copy() for ids in tokenized["input_ids"]]
        return tokenized

    dataset = Dataset.from_list(examples)
    if is_encoder_decoder:
        tokenized = dataset.map(tokenize_seq2seq, batched=True, remove_columns=dataset.column_names)
        collator = DataCollatorForSeq2Seq(tokenizer, model=model)
    else:
        tokenized = dataset.map(tokenize_causal, batched=True, remove_columns=dataset.column_names)
        collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

    output_dir = Path(config.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=config.grad_accum,
        learning_rate=config.learning_rate,
        logging_steps=5,
        save_strategy="no",
        report_to=[],
        seed=config.seed,
        fp16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=collator,
    )
    trainer.train()

    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    (output_dir / "train_config.json").write_text(config.to_json(), encoding="utf-8")
    print(f"Saved LoRA adapter and tokenizer to {output_dir}")
    print("Reminder: tuning/outputs/ is gitignored. Do NOT commit weights/adapters.")
    return 0


def main(argv: list[str] | None = None) -> int:
    print(GPU_BANNER)
    print("-" * 60)
    args = parse_args(argv)
    config = config_from_args(args)

    if args.smoke_test:
        return run_smoke_test(config)
    return run_training(config)


if __name__ == "__main__":
    raise SystemExit(main())
