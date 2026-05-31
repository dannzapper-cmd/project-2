#!/usr/bin/env python3
"""Validate the SnapInsight product-intelligence tuning dataset.

CPU-only, no GPU, no model download. Designed to finish in well under 10
seconds on the seed dataset. Validates that each JSONL record:

- is valid JSON,
- has an ``input`` object with at least a non-empty ``product_name``,
- has an ``output`` object that conforms to the canonical schema
  (see ``schemas.py``),
- contains no medical claim in ``safe_summary``,
- uses only known input/output keys (warns on unknown keys).

It also prints a small distribution report (difficulty buckets, caution
levels, medical-claim flags) so dataset balance is visible.

Usage:
    python3 tuning/src/validate_dataset.py tuning/data/product_intelligence_seed.jsonl

Exit code is 0 when the dataset is valid, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Allow running directly (python3 tuning/src/validate_dataset.py ...) by making
# the sibling ``schemas`` module importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import (  # noqa: E402
    CAUTION_LEVELS,
    INPUT_FIELDS,
    OUTPUT_FIELDS,
    validate_output,
)

ALLOWED_TOP_LEVEL_KEYS = {"id", "difficulty", "split", "input", "output", "notes"}
KNOWN_INPUT_KEYS = set(INPUT_FIELDS)

SPLIT_CHOICES = ("all", "train", "eval")
DEFAULT_HOLDOUT_FRAC = 0.2


@dataclass
class DatasetReport:
    """Aggregate result of validating a dataset file."""

    path: str
    total_records: int = 0
    valid_records: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    difficulty_counts: Counter = field(default_factory=Counter)
    caution_counts: Counter = field(default_factory=Counter)
    category_counts: Counter = field(default_factory=Counter)
    medical_claim_flag_count: int = 0
    train_count: int = 0
    eval_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors and self.total_records > 0


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSONL file, raising ValueError with the line number on bad JSON."""

    records: list[dict[str, Any]] = []
    text = Path(path).read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {lineno}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"line {lineno}: record is not a JSON object")
        records.append(obj)
    return records


def _record_key(record: dict[str, Any], index: int) -> str:
    """Stable key for splitting: prefer the record id, fall back to its index."""

    rid = record.get("id")
    return str(rid) if isinstance(rid, str) and rid else f"__index_{index}"


def deterministic_split(
    records: list[dict[str, Any]],
    *,
    split: str = "all",
    holdout_frac: float = DEFAULT_HOLDOUT_FRAC,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Return a reproducible train/eval subset of ``records``.

    The split is content-addressed: each record is assigned to the eval holdout
    iff a stable hash of ``seed`` + its id (or index) falls below ``holdout_frac``.
    This is deterministic across runs and machines and does not depend on order,
    so ``--split eval`` always yields the same held-out set.

    ``split="all"`` (the default) returns every record unchanged, which keeps the
    default behavior of the scripts and tests stable. Use ``split="train"`` for
    training and ``split="eval"`` for an honest held-out evaluation.

    A record may also pin itself with an explicit ``"split": "train"|"eval"``
    field, which overrides the hash assignment.
    """

    if split not in SPLIT_CHOICES:
        raise ValueError(f"split must be one of {SPLIT_CHOICES}, got {split!r}")
    if split == "all":
        return list(records)
    if not 0.0 < holdout_frac < 1.0:
        raise ValueError("holdout_frac must be between 0 and 1 (exclusive)")

    selected: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        pinned = record.get("split")
        if pinned in ("train", "eval"):
            assigned = pinned
        else:
            digest = hashlib.md5(f"{seed}:{_record_key(record, index)}".encode()).hexdigest()
            fraction = int(digest[:8], 16) / 0xFFFFFFFF
            assigned = "eval" if fraction < holdout_frac else "train"
        if assigned == split:
            selected.append(record)
    return selected


def validate_record(record: dict[str, Any], *, ref: str) -> tuple[list[str], list[str]]:
    """Validate a single dataset record.

    Returns ``(errors, warnings)``. ``ref`` is a human-readable record id used
    in messages (e.g. the record's ``id`` field or its line number).
    """

    errors: list[str] = []
    warnings: list[str] = []

    unknown_top = set(record) - ALLOWED_TOP_LEVEL_KEYS
    if unknown_top:
        warnings.append(f"{ref}: unknown top-level keys {sorted(unknown_top)}")

    record_input = record.get("input")
    if not isinstance(record_input, dict):
        errors.append(f"{ref}: 'input' must be an object")
    else:
        name = record_input.get("product_name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{ref}: input.product_name must be a non-empty string")
        unknown_input = set(record_input) - KNOWN_INPUT_KEYS
        if unknown_input:
            warnings.append(f"{ref}: unknown input keys {sorted(unknown_input)}")

    record_output = record.get("output")
    if not isinstance(record_output, dict):
        errors.append(f"{ref}: 'output' must be an object")
        return errors, warnings

    result = validate_output(record_output)
    if not result.valid:
        for err in result.errors:
            errors.append(f"{ref}: output {err}")

    return errors, warnings


def validate_dataset(path: str | Path) -> DatasetReport:
    """Validate an entire dataset file and return a structured report."""

    report = DatasetReport(path=str(path))
    try:
        records = load_jsonl(path)
    except (OSError, ValueError) as exc:
        report.errors.append(str(exc))
        return report

    report.total_records = len(records)
    if not records:
        report.errors.append("dataset is empty")
        return report

    seen_ids: set[str] = set()
    for idx, record in enumerate(records, start=1):
        ref = str(record.get("id") or f"line {idx}")

        record_id = record.get("id")
        if isinstance(record_id, str):
            if record_id in seen_ids:
                report.errors.append(f"{ref}: duplicate id")
            seen_ids.add(record_id)

        errors, warnings = validate_record(record, ref=ref)
        report.errors.extend(errors)
        report.warnings.extend(warnings)
        if not errors:
            report.valid_records += 1

        difficulty = record.get("difficulty", "unspecified")
        report.difficulty_counts[difficulty] += 1

        output = record.get("output")
        if isinstance(output, dict):
            caution = output.get("caution_level")
            if caution in CAUTION_LEVELS:
                report.caution_counts[caution] += 1
            category = output.get("normalized_category")
            if isinstance(category, str):
                report.category_counts[category] += 1
            if output.get("medical_claim_detected") is True:
                report.medical_claim_flag_count += 1

    # Report the default reproducible holdout sizes so the split is visible.
    report.train_count = len(deterministic_split(records, split="train"))
    report.eval_count = len(deterministic_split(records, split="eval"))

    return report


def print_report(report: DatasetReport) -> None:
    print(f"Dataset: {report.path}")
    print(f"Records: {report.total_records} (valid: {report.valid_records})")
    print(f"Required output fields: {list(OUTPUT_FIELDS)}")

    if report.difficulty_counts:
        print("Difficulty distribution:")
        for key, count in sorted(report.difficulty_counts.items()):
            print(f"  - {key}: {count}")
    if report.caution_counts:
        print("Caution-level distribution:")
        for key in CAUTION_LEVELS:
            if report.caution_counts.get(key):
                print(f"  - {key}: {report.caution_counts[key]}")
    print(f"Records flagging a source medical/health claim: {report.medical_claim_flag_count}")
    print(f"Unique normalized categories: {len(report.category_counts)}")
    print(
        "Reproducible holdout (default frac=%.0f%%, seed=42): train=%d, eval=%d"
        % (DEFAULT_HOLDOUT_FRAC * 100, report.train_count, report.eval_count)
    )

    if report.warnings:
        print(f"\nWarnings ({len(report.warnings)}):")
        for warning in report.warnings:
            print(f"  ! {warning}")

    if report.errors:
        print(f"\nFAIL: {len(report.errors)} error(s):")
        for err in report.errors:
            print(f"  - {err}")
    else:
        print("\nPASS: dataset is valid against the canonical schema.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the product-intelligence tuning dataset.")
    parser.add_argument(
        "path",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1] / "data" / "product_intelligence_seed.jsonl"),
        help="Path to the JSONL dataset (defaults to the seed dataset).",
    )
    args = parser.parse_args(argv)

    report = validate_dataset(args.path)
    print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
