#!/usr/bin/env python3
"""Baseline vs tuned evaluation for the SnapInsight product-intelligence task.

Computes the metrics required by Block 18C against the canonical schema:

- valid JSON rate
- required-fields-present rate
- normalized-category accuracy (where labels exist)
- caution-level accuracy
- warning-label accuracy (set precision/recall/F1, a partial match)
- medical-claim violation count (banned text in generated safe_summary)
- exact structured match and average partial field match

Two ways to run:

1. ``--mock`` (CPU, no model): generate deterministic "baseline" and "tuned"
   predictions from the dataset and score the eval logic. Used by smoke tests
   and for demonstrating the report format honestly without a trained model.

2. real model: pass ``--model <path-or-id>`` to load a (LoRA-adapted) model and
   score its generations. Requires torch/transformers/peft and is best on GPU.

Example (mock, no model):

    python3 tuning/src/evaluate.py --mock \\
        --data tuning/data/product_intelligence_seed.jsonl \\
        --report tuning/reports/eval_report.md

The metric functions here are pure and import-safe so tests can call them with
fixture outputs without loading any model.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import (  # noqa: E402
    OUTPUT_FIELDS,
    canonical_output,
    detect_medical_claim,
    parse_output,
    render_output_json,
    validate_output,
)
from validate_dataset import load_jsonl  # noqa: E402

DEFAULT_DATA = str(
    Path(__file__).resolve().parents[1] / "data" / "product_intelligence_seed.jsonl"
)
LIST_FIELDS = ("product_attributes", "nutrition_flags", "warning_labels", "suggested_questions")


@dataclass
class EvalMetrics:
    """Aggregate metrics for one prediction set (e.g. baseline or tuned)."""

    label: str
    n: int = 0
    valid_json: int = 0
    schema_valid: int = 0
    category_total: int = 0
    category_correct: int = 0
    caution_total: int = 0
    caution_correct: int = 0
    warning_precision_sum: float = 0.0
    warning_recall_sum: float = 0.0
    warning_f1_sum: float = 0.0
    warning_examples: int = 0
    medical_claim_violations: int = 0
    exact_match: int = 0
    partial_match_sum: float = 0.0

    @property
    def valid_json_rate(self) -> float:
        return self.valid_json / self.n if self.n else 0.0

    @property
    def required_fields_rate(self) -> float:
        return self.schema_valid / self.n if self.n else 0.0

    @property
    def category_accuracy(self) -> float:
        return self.category_correct / self.category_total if self.category_total else 0.0

    @property
    def caution_accuracy(self) -> float:
        return self.caution_correct / self.caution_total if self.caution_total else 0.0

    @property
    def warning_f1(self) -> float:
        return self.warning_f1_sum / self.warning_examples if self.warning_examples else 0.0

    @property
    def exact_match_rate(self) -> float:
        return self.exact_match / self.n if self.n else 0.0

    @property
    def partial_match_rate(self) -> float:
        return self.partial_match_sum / self.n if self.n else 0.0

    def to_dict(self) -> dict[str, Any]:
        base = asdict(self)
        base.update(
            {
                "valid_json_rate": round(self.valid_json_rate, 4),
                "required_fields_rate": round(self.required_fields_rate, 4),
                "category_accuracy": round(self.category_accuracy, 4),
                "caution_accuracy": round(self.caution_accuracy, 4),
                "warning_f1": round(self.warning_f1, 4),
                "exact_match_rate": round(self.exact_match_rate, 4),
                "partial_match_rate": round(self.partial_match_rate, 4),
            }
        )
        return base


def _norm(value: Any) -> str:
    return str(value).strip().lower()


def _set_prf(predicted: list[str], reference: list[str]) -> tuple[float, float, float]:
    """Set-based precision/recall/F1 over normalized string items."""

    pred_set = {_norm(x) for x in predicted}
    ref_set = {_norm(x) for x in reference}
    if not pred_set and not ref_set:
        return 1.0, 1.0, 1.0
    if not pred_set or not ref_set:
        return 0.0, 0.0, 0.0
    overlap = len(pred_set & ref_set)
    precision = overlap / len(pred_set)
    recall = overlap / len(ref_set)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def _partial_field_match(pred: dict[str, Any], ref: dict[str, Any]) -> float:
    """Average per-field agreement between a prediction and reference output."""

    scores: list[float] = []
    for field_name in OUTPUT_FIELDS:
        ref_value = ref.get(field_name)
        pred_value = pred.get(field_name)
        if field_name in LIST_FIELDS:
            _, _, f1 = _set_prf(
                pred_value if isinstance(pred_value, list) else [],
                ref_value if isinstance(ref_value, list) else [],
            )
            scores.append(f1)
        elif field_name == "medical_claim_detected":
            scores.append(1.0 if bool(pred_value) == bool(ref_value) else 0.0)
        else:
            scores.append(1.0 if _norm(pred_value) == _norm(ref_value) else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def compute_metrics(
    label: str,
    references: list[dict[str, Any]],
    raw_predictions: list[str],
) -> EvalMetrics:
    """Score raw prediction strings against reference output dicts."""

    if len(references) != len(raw_predictions):
        raise ValueError("references and predictions must be the same length")

    metrics = EvalMetrics(label=label, n=len(references))

    for ref, raw in zip(references, raw_predictions):
        parsed, error = parse_output(raw)
        if error is not None or not isinstance(parsed, dict):
            # Unparseable output: still scan the raw text for medical claims.
            if detect_medical_claim(raw or ""):
                metrics.medical_claim_violations += 1
            continue
        metrics.valid_json += 1

        result = validate_output(parsed)
        if result.valid:
            metrics.schema_valid += 1

        # Medical-claim violation: banned text in the generated safe_summary.
        summary = parsed.get("safe_summary", "")
        if isinstance(summary, str) and detect_medical_claim(summary):
            metrics.medical_claim_violations += 1

        # Category accuracy (only where a reference label exists).
        ref_category = ref.get("normalized_category")
        if isinstance(ref_category, str) and ref_category.strip():
            metrics.category_total += 1
            if _norm(parsed.get("normalized_category")) == _norm(ref_category):
                metrics.category_correct += 1

        # Caution-level accuracy.
        if "caution_level" in ref:
            metrics.caution_total += 1
            if _norm(parsed.get("caution_level")) == _norm(ref.get("caution_level")):
                metrics.caution_correct += 1

        # Warning-label set accuracy.
        if "warning_labels" in ref:
            precision, recall, f1 = _set_prf(
                parsed.get("warning_labels") if isinstance(parsed.get("warning_labels"), list) else [],
                ref.get("warning_labels") if isinstance(ref.get("warning_labels"), list) else [],
            )
            metrics.warning_precision_sum += precision
            metrics.warning_recall_sum += recall
            metrics.warning_f1_sum += f1
            metrics.warning_examples += 1

        # Exact + partial structured match.
        if canonical_output(parsed) == canonical_output(ref):
            metrics.exact_match += 1
        metrics.partial_match_sum += _partial_field_match(parsed, ref)

    return metrics


# ---------------------------------------------------------------------------
# Mock predictions (CPU, no model) -- demonstrate baseline vs tuned honestly.
# ---------------------------------------------------------------------------


def mock_tuned_prediction(ref: dict[str, Any]) -> str:
    """A 'tuned' model is expected to closely reproduce the schema target.

    We inject a small, deterministic imperfection on a subset of records so the
    tuned scores are realistic (not a perfect 1.0) rather than fabricated.
    """

    out = dict(canonical_output(ref))
    # Deterministic minor error: drop the last suggested question occasionally.
    name = str(ref.get("normalized_category", ""))
    if len(name) % 5 == 0 and len(out.get("suggested_questions", [])) > 1:
        out["suggested_questions"] = out["suggested_questions"][:-1]
    return render_output_json(out)


def mock_baseline_prediction(ref: dict[str, Any]) -> str:
    """An untuned small base model: often emits prose / partial / unsafe JSON.

    Deterministic per record so tests are stable. This intentionally produces
    lower scores to demonstrate that the eval logic separates baseline vs tuned.
    """

    category = str(ref.get("normalized_category", "Food"))
    bucket = len(category) % 3
    if bucket == 0:
        # Plain prose, not JSON at all.
        return f"This product looks like {category}. It seems fine to me."
    if bucket == 1:
        # Partial JSON missing required fields, and overclaiming.
        return json.dumps(
            {
                "normalized_category": category,
                "safe_summary": "This is a healthy product and is safe to eat.",
            }
        )
    # Structurally complete JSON but with a wrong caution level and empty lists.
    wrong_caution = "none" if ref.get("caution_level") != "none" else "high"
    return render_output_json(
        {
            "normalized_category": category,
            "product_attributes": [],
            "nutrition_flags": [],
            "warning_labels": [],
            "caution_level": wrong_caution,
            "suggested_questions": [],
            "safe_summary": f"A {category} product.",
            "medical_claim_detected": False,
        }
    )


def references_from_dataset(data_path: str) -> list[dict[str, Any]]:
    records = load_jsonl(data_path)
    return [canonical_output(r.get("output") or {}) for r in records]


# ---------------------------------------------------------------------------
# Real model prediction (lazy import; GPU recommended)
# ---------------------------------------------------------------------------


def generate_real_predictions(model_path: str, data_path: str, max_new_tokens: int = 320) -> list[str]:
    """Load a (LoRA-adapted) model and generate raw predictions for each record."""

    try:
        import torch  # noqa: F401
        from peft import PeftConfig, PeftModel
        from transformers import (
            AutoConfig,
            AutoModelForCausalLM,
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
        )
    except ImportError as exc:  # pragma: no cover - optional deps
        raise SystemExit(
            "Real evaluation needs torch/transformers/peft. Install with "
            "'pip install -r tuning/requirements.txt' or use --mock."
        ) from exc

    from schemas import build_prompt

    # Resolve base model: if model_path is a PEFT adapter dir, read its base.
    base_model_name = model_path
    is_adapter = (Path(model_path) / "adapter_config.json").exists()
    if is_adapter:
        base_model_name = PeftConfig.from_pretrained(model_path).base_model_name_or_path

    hf_config = AutoConfig.from_pretrained(base_model_name)
    is_encoder_decoder = bool(getattr(hf_config, "is_encoder_decoder", False))
    tokenizer = AutoTokenizer.from_pretrained(model_path if not is_adapter else base_model_name)
    loader = AutoModelForSeq2SeqLM if is_encoder_decoder else AutoModelForCausalLM
    model = loader.from_pretrained(base_model_name)
    if is_adapter:
        model = PeftModel.from_pretrained(model, model_path)
    model.eval()

    records = load_jsonl(data_path)
    predictions: list[str] = []
    for record in records:
        prompt = build_prompt(record.get("input") or {})
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
        if is_encoder_decoder:
            text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        else:
            text = tokenizer.decode(
                output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
            )
        predictions.append(text)
    return predictions


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def build_report(
    data_path: str,
    model_label: str,
    metrics_by_label: dict[str, EvalMetrics],
) -> str:
    lines: list[str] = []
    lines.append("# SnapInsight 18C — Tuning Evaluation Report")
    lines.append("")
    lines.append(f"- Dataset: `{data_path}`")
    lines.append(f"- Evaluated: {model_label}")
    lines.append("")
    lines.append(
        "> This report scores structured product-intelligence outputs against the "
        "canonical schema in `tuning/src/schemas.py`. It does not measure production "
        "SnapInsight behavior and does not validate medical accuracy."
    )
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    header = "| Metric | " + " | ".join(metrics_by_label.keys()) + " |"
    sep = "|" + "---|" * (len(metrics_by_label) + 1)
    lines.append(header)
    lines.append(sep)

    rows = [
        ("Valid JSON rate", lambda m: _fmt_pct(m.valid_json_rate)),
        ("Required fields present", lambda m: _fmt_pct(m.required_fields_rate)),
        ("Category accuracy", lambda m: _fmt_pct(m.category_accuracy)),
        ("Caution-level accuracy", lambda m: _fmt_pct(m.caution_accuracy)),
        ("Warning-label F1", lambda m: _fmt_pct(m.warning_f1)),
        ("Exact structured match", lambda m: _fmt_pct(m.exact_match_rate)),
        ("Partial field match", lambda m: _fmt_pct(m.partial_match_rate)),
        ("Medical-claim violations", lambda m: str(m.medical_claim_violations)),
        ("Examples (n)", lambda m: str(m.n)),
    ]
    for name, fn in rows:
        cells = " | ".join(fn(m) for m in metrics_by_label.values())
        lines.append(f"| {name} | {cells} |")

    lines.append("")
    lines.append("## Raw metric JSON")
    lines.append("")
    lines.append("```json")
    lines.append(
        json.dumps({k: v.to_dict() for k, v in metrics_by_label.items()}, indent=2)
    )
    lines.append("```")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `medical_claim_violations` counts generated summaries that contain banned")
    lines.append("  medical/absolute-health phrasing; the target is **0**.")
    lines.append("- Warning-label F1 is a set-overlap partial metric, not exact match.")
    lines.append("- A tuned model should improve valid-JSON, required-fields, and accuracy")
    lines.append("  metrics over the untuned baseline while keeping violations at 0.")
    return "\n".join(lines) + "\n"


def run_mock(data_path: str, report_path: str | None) -> int:
    references = references_from_dataset(data_path)
    baseline_preds = [mock_baseline_prediction(r) for r in references]
    tuned_preds = [mock_tuned_prediction(r) for r in references]

    baseline = compute_metrics("baseline (mock)", references, baseline_preds)
    tuned = compute_metrics("tuned (mock)", references, tuned_preds)
    metrics_by_label = {"baseline (mock)": baseline, "tuned (mock)": tuned}

    report = build_report(data_path, "MOCK predictions (no model loaded)", metrics_by_label)
    print(report)
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(report, encoding="utf-8")
        print(f"Wrote report to {report_path}")
    return 0


def run_real(model_path: str, data_path: str, report_path: str | None) -> int:
    predictions = generate_real_predictions(model_path, data_path)
    references = references_from_dataset(data_path)
    metrics = compute_metrics(f"model: {model_path}", references, predictions)
    metrics_by_label = {f"tuned ({model_path})": metrics}
    report = build_report(data_path, f"model at {model_path}", metrics_by_label)
    print(report)
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(report, encoding="utf-8")
        print(f"Wrote report to {report_path}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate product-intelligence outputs.")
    parser.add_argument("--model", default=None, help="Path/id of a model to evaluate (omit with --mock).")
    parser.add_argument("--data", default=DEFAULT_DATA, help="JSONL dataset of references.")
    parser.add_argument("--report", default=None, help="Optional path to write a Markdown report.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run eval logic against deterministic mock baseline/tuned predictions (no model).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mock or not args.model:
        if not args.mock:
            print("No --model provided; running in --mock mode.\n")
        return run_mock(args.data, args.report)
    return run_real(args.model, args.data, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
