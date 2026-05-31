"""Smoke tests for the SnapInsight 18C tuning pipeline.

CPU-only, no GPU, no model download. These tests validate the seed dataset, the
schema, the dataset-validation logic, the evaluation metrics (against mock
fixture outputs), the Vertex SFT export format, and the train smoke path.

Run with:
    python3 -m pytest tuning/tests -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the tuning src modules importable without installing a package.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "product_intelligence_seed.jsonl"
sys.path.insert(0, str(SRC_DIR))

import build_vertex_sft_jsonl as vertex  # noqa: E402
import evaluate as ev  # noqa: E402
import train_lora  # noqa: E402
from schemas import (  # noqa: E402
    CAUTION_LEVELS,
    OUTPUT_FIELDS,
    build_prompt,
    detect_medical_claim,
    parse_output,
    render_output_json,
    validate_output,
)
from validate_dataset import (  # noqa: E402
    deterministic_split,
    load_jsonl,
    validate_dataset,
    validate_record,
)


# ---------------------------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------------------------


def test_seed_dataset_is_valid():
    report = validate_dataset(DATA_PATH)
    assert report.ok, f"seed dataset invalid: {report.errors}"
    assert report.total_records == report.valid_records
    assert 30 <= report.total_records <= 80


def test_seed_dataset_has_difficulty_diversity():
    report = validate_dataset(DATA_PATH)
    # Must contain easy, ambiguous, missing-data and do-not-overclaim cases.
    for bucket in ("easy", "ambiguous", "missing", "overclaim"):
        assert report.difficulty_counts.get(bucket, 0) > 0, f"missing '{bucket}' cases"


def test_seed_dataset_has_overclaim_flags():
    report = validate_dataset(DATA_PATH)
    assert report.medical_claim_flag_count >= 1


def test_validate_record_flags_missing_output_field():
    record = {
        "id": "bad-1",
        "input": {"product_name": "Test"},
        "output": {
            # missing several required fields
            "normalized_category": "Snack",
            "caution_level": "low",
        },
    }
    errors, _ = validate_record(record, ref="bad-1")
    assert any("missing required field" in e for e in errors)


def test_validate_record_flags_bad_caution_level():
    output = {f: ([] if f.endswith("s") or "labels" in f or "attributes" in f or "flags" in f else "") for f in OUTPUT_FIELDS}
    output["normalized_category"] = "Snack"
    output["caution_level"] = "extreme"  # invalid enum
    output["safe_summary"] = "A snack."
    output["medical_claim_detected"] = False
    record = {"id": "bad-2", "input": {"product_name": "Test"}, "output": output}
    errors, _ = validate_record(record, ref="bad-2")
    assert any("caution_level" in e for e in errors)


def test_validate_record_flags_missing_product_name():
    record = {
        "id": "bad-3",
        "input": {"brand": "X"},
        "output": _good_output(),
    }
    errors, _ = validate_record(record, ref="bad-3")
    assert any("product_name" in e for e in errors)


def test_validate_record_flags_medical_claim_in_summary():
    output = _good_output()
    output["safe_summary"] = "This product cures diabetes and is safe to eat for everyone."
    record = {"id": "bad-4", "input": {"product_name": "Test"}, "output": output}
    errors, _ = validate_record(record, ref="bad-4")
    assert any("medical claim" in e for e in errors)


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _good_output() -> dict:
    return {
        "normalized_category": "Snack",
        "product_attributes": ["vegan"],
        "nutrition_flags": ["high sugar"],
        "warning_labels": ["allergen: peanuts"],
        "caution_level": "medium",
        "suggested_questions": ["What is the serving size?"],
        "safe_summary": "A snack with high sugar and peanuts.",
        "medical_claim_detected": False,
    }


def test_validate_output_accepts_good_object():
    assert validate_output(_good_output()).valid


def test_validate_output_rejects_wrong_types():
    bad = _good_output()
    bad["product_attributes"] = "not a list"
    result = validate_output(bad)
    assert not result.valid


def test_validate_output_rejects_non_bool_flag():
    bad = _good_output()
    bad["medical_claim_detected"] = "false"
    result = validate_output(bad)
    assert not result.valid


def test_detect_medical_claim_patterns():
    assert detect_medical_claim("this cures cancer")
    assert detect_medical_claim("it is healthy")
    assert detect_medical_claim("safe to eat for diabetics")
    assert not detect_medical_claim("a tomato pasta sauce with moderate salt")


@pytest.mark.parametrize(
    "raw",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        'Sure! Here is the answer: {"a": 1} hope that helps',
    ],
)
def test_parse_output_tolerant(raw):
    obj, err = parse_output(raw)
    assert err is None
    assert obj == {"a": 1}


def test_parse_output_handles_garbage():
    obj, err = parse_output("no json here")
    assert obj is None
    assert err is not None


def test_caution_levels_constant():
    assert CAUTION_LEVELS == ("none", "low", "medium", "high")


# ---------------------------------------------------------------------------
# Evaluation metrics (mock fixtures, no model)
# ---------------------------------------------------------------------------


def test_compute_metrics_perfect_match():
    ref = _good_output()
    metrics = ev.compute_metrics("perfect", [ref], [render_output_json(ref)])
    assert metrics.valid_json_rate == 1.0
    assert metrics.required_fields_rate == 1.0
    assert metrics.category_accuracy == 1.0
    assert metrics.caution_accuracy == 1.0
    assert metrics.warning_f1 == 1.0
    assert metrics.exact_match_rate == 1.0
    assert metrics.medical_claim_violations == 0


def test_compute_metrics_counts_medical_violation():
    ref = _good_output()
    bad_pred = dict(ref)
    bad_pred["safe_summary"] = "This product cures illness."
    metrics = ev.compute_metrics("bad", [ref], [json.dumps(bad_pred)])
    assert metrics.medical_claim_violations == 1


def test_compute_metrics_invalid_json_lowers_rate():
    ref = _good_output()
    metrics = ev.compute_metrics("prose", [ref], ["this is just prose"])
    assert metrics.valid_json_rate == 0.0
    assert metrics.required_fields_rate == 0.0


def test_compute_metrics_length_mismatch_raises():
    with pytest.raises(ValueError):
        ev.compute_metrics("x", [_good_output()], [])


def test_mock_eval_baseline_worse_than_tuned():
    references = ev.references_from_dataset(str(DATA_PATH))
    baseline = ev.compute_metrics(
        "baseline", references, [ev.mock_baseline_prediction(r) for r in references]
    )
    tuned = ev.compute_metrics(
        "tuned", references, [ev.mock_tuned_prediction(r) for r in references]
    )
    # The tuned mock must clearly beat the baseline mock on key metrics.
    assert tuned.required_fields_rate > baseline.required_fields_rate
    assert tuned.exact_match_rate > baseline.exact_match_rate
    assert tuned.medical_claim_violations == 0
    assert baseline.medical_claim_violations > 0


def test_build_report_contains_metric_rows():
    references = ev.references_from_dataset(str(DATA_PATH))
    tuned = ev.compute_metrics(
        "tuned", references, [ev.mock_tuned_prediction(r) for r in references]
    )
    report = ev.build_report(str(DATA_PATH), "mock", {"tuned": tuned})
    assert "Valid JSON rate" in report
    assert "Medical-claim violations" in report


# ---------------------------------------------------------------------------
# Prompt building + Vertex export
# ---------------------------------------------------------------------------


def test_build_prompt_includes_metadata_fields():
    prompt = build_prompt(
        {"product_name": "Test Bar", "brand": "Acme", "category": "snack"}
    )
    assert "Test Bar" in prompt
    assert "Acme" in prompt
    assert "JSON:" in prompt


def test_build_prompt_handles_missing_fields():
    prompt = build_prompt({"product_name": "Mystery"})
    assert "unknown" in prompt  # missing fields rendered as 'unknown'


def test_vertex_export_format():
    records = vertex.build_vertex_records(str(DATA_PATH))
    assert len(records) >= 30
    for record in records:
        assert set(record.keys()) == {"input_text", "output_text"}
        assert isinstance(record["input_text"], str) and record["input_text"]
        # output_text must itself be valid JSON conforming to the schema.
        parsed = json.loads(record["output_text"])
        assert validate_output(parsed).valid


def test_vertex_export_writes_jsonl(tmp_path):
    out = tmp_path / "vertex_sft.jsonl"
    records = vertex.build_vertex_records(str(DATA_PATH))
    vertex.write_jsonl(records, str(out))
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(records)
    for line in lines:
        obj = json.loads(line)
        assert set(obj.keys()) == {"input_text", "output_text"}


# ---------------------------------------------------------------------------
# Training smoke path (no model download, no torch)
# ---------------------------------------------------------------------------


def test_train_build_examples():
    examples = train_lora.build_examples(str(DATA_PATH))
    assert len(examples) >= 30
    for example in examples[:5]:
        assert "prompt" in example and "target" in example
        parsed = json.loads(example["target"])
        assert validate_output(parsed).valid


def test_train_smoke_test_passes(capsys):
    args = train_lora.parse_args(["--smoke-test", "--data", str(DATA_PATH)])
    config = train_lora.config_from_args(args)
    rc = train_lora.run_smoke_test(config)
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASS" in out


def test_train_config_validation_catches_bad_values():
    args = train_lora.parse_args(["--epochs", "0", "--data", str(DATA_PATH)])
    config = train_lora.config_from_args(args)
    problems = train_lora.validate_config(config)
    assert any("epochs" in p for p in problems)


def test_train_split_train_selects_fewer_than_all():
    full = train_lora.build_examples(str(DATA_PATH), split="all")
    train = train_lora.build_examples(str(DATA_PATH), split="train")
    eval_ex = train_lora.build_examples(str(DATA_PATH), split="eval")
    assert len(train) < len(full)
    assert len(train) + len(eval_ex) == len(full)
    assert len(eval_ex) > 0


# ---------------------------------------------------------------------------
# Reproducible train/eval split
# ---------------------------------------------------------------------------


def test_deterministic_split_all_returns_everything():
    records = load_jsonl(str(DATA_PATH))
    assert len(deterministic_split(records, split="all")) == len(records)


def test_deterministic_split_disjoint_and_covers_all():
    records = load_jsonl(str(DATA_PATH))
    train = deterministic_split(records, split="train")
    holdout = deterministic_split(records, split="eval")
    train_ids = {r["id"] for r in train}
    eval_ids = {r["id"] for r in holdout}
    assert train_ids.isdisjoint(eval_ids)
    assert train_ids | eval_ids == {r["id"] for r in records}
    assert len(holdout) > 0 and len(train) > 0


def test_deterministic_split_is_reproducible():
    records = load_jsonl(str(DATA_PATH))
    first = [r["id"] for r in deterministic_split(records, split="eval")]
    second = [r["id"] for r in deterministic_split(records, split="eval")]
    assert first == second


def test_deterministic_split_holdout_spans_difficulties():
    records = load_jsonl(str(DATA_PATH))
    holdout = deterministic_split(records, split="eval")
    buckets = {r.get("difficulty") for r in holdout}
    # The held-out set should not be trivially one difficulty bucket.
    assert len(buckets) >= 3


def test_deterministic_split_respects_pinned_field():
    records = [
        {"id": "p1", "split": "eval", "input": {}, "output": {}},
        {"id": "p2", "split": "train", "input": {}, "output": {}},
    ]
    eval_ids = {r["id"] for r in deterministic_split(records, split="eval")}
    train_ids = {r["id"] for r in deterministic_split(records, split="train")}
    assert eval_ids == {"p1"}
    assert train_ids == {"p2"}


def test_deterministic_split_rejects_bad_split():
    with pytest.raises(ValueError):
        deterministic_split([], split="nonsense")


# ---------------------------------------------------------------------------
# Report provenance + honesty disclaimers
# ---------------------------------------------------------------------------


def test_mock_report_flags_itself_as_evaluator_validation():
    references = ev.references_from_dataset(str(DATA_PATH))
    tuned = ev.compute_metrics(
        "tuned", references, [ev.mock_tuned_prediction(r) for r in references]
    )
    report = ev.build_report(str(DATA_PATH), "mock", {"tuned": tuned}, split="all", is_mock=True)
    assert "validates the evaluator" in report
    assert "Run metadata" in report
    assert "Generated at" in report


def test_report_split_all_warns_in_sample():
    references = ev.references_from_dataset(str(DATA_PATH))
    tuned = ev.compute_metrics(
        "tuned", references, [ev.mock_tuned_prediction(r) for r in references]
    )
    report = ev.build_report(str(DATA_PATH), "m", {"tuned": tuned}, split="all")
    assert "in-sample" in report


def test_eval_on_holdout_split_runs():
    refs = ev.references_from_dataset(str(DATA_PATH), split="eval")
    assert 0 < len(refs) < 45
    metrics = ev.compute_metrics("eval", refs, [ev.mock_tuned_prediction(r) for r in refs])
    assert metrics.n == len(refs)
