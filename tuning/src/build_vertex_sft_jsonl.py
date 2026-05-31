#!/usr/bin/env python3
"""Export the product-intelligence dataset to a Vertex AI supervised tuning JSONL.

This converts the SAME seed dataset used for local LoRA training into the
supervised fine-tuning (SFT) JSONL format that Google Cloud's Vertex AI
Supervised Tuning expects, so the data could later be reused on an enterprise
tuning path WITHOUT re-labeling.

Output format (one JSON object per line):

    {"input_text": "<prompt>", "output_text": "<json_response>"}

This `input_text` / `output_text` pairing matches the Vertex AI Supervised
Tuning JSONL spec for text models. See Google Cloud docs:
https://cloud.google.com/vertex-ai/generative-ai/docs/models/tune-models

This script does NOT call any Google API, does NOT require credentials, and adds
NO google-cloud dependencies. It only reads the local dataset and writes a local
JSONL file using the shared prompt builder in `schemas.py`.

Usage:
    python3 tuning/src/build_vertex_sft_jsonl.py \\
        --data tuning/data/product_intelligence_seed.jsonl \\
        --output tuning/outputs/vertex_sft.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas import build_prompt, render_output_json  # noqa: E402
from validate_dataset import load_jsonl  # noqa: E402

DEFAULT_DATA = str(
    Path(__file__).resolve().parents[1] / "data" / "product_intelligence_seed.jsonl"
)
DEFAULT_OUTPUT = str(Path(__file__).resolve().parents[1] / "outputs" / "vertex_sft.jsonl")


def build_vertex_records(data_path: str) -> list[dict[str, str]]:
    """Build Vertex SFT records ({"input_text", "output_text"}) from the dataset."""

    records = load_jsonl(data_path)
    vertex_records: list[dict[str, str]] = []
    for record in records:
        prompt = build_prompt(record.get("input") or {})
        target = render_output_json(record.get("output") or {})
        vertex_records.append({"input_text": prompt, "output_text": target})
    return vertex_records


def write_jsonl(records: list[dict[str, str]], output_path: str) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in records:
            # One JSON object per line, exactly two keys, no trailing whitespace.
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export dataset to Vertex AI SFT JSONL.")
    parser.add_argument("--data", default=DEFAULT_DATA, help="Source JSONL dataset.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Destination JSONL path.")
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the records to stdout instead of writing a file (no outputs/ write).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records = build_vertex_records(args.data)

    if args.print_only:
        for record in records:
            print(json.dumps(record, ensure_ascii=False))
        return 0

    write_jsonl(records, args.output)
    print(f"Wrote {len(records)} Vertex SFT records to {args.output}")
    print('Format: {"input_text": "<prompt>", "output_text": "<json_response>"}')
    print("Reminder: tuning/outputs/ is gitignored. This export is not committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
