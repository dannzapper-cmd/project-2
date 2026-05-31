"""Canonical schema for the SnapInsight Block 18C product-intelligence tuning task.

This is the SINGLE source of truth for the tuned model's output contract. Both
``train_lora.py`` (for building targets) and ``evaluate.py`` (for scoring
predictions) import and validate against the structures defined here. Do not
redefine the schema inline anywhere else.

The tuned task is TEXT/METADATA based, not multimodal. Given structured product
metadata (name, brand, category, ingredients, nutrition, OpenFoodFacts-style
fields, existing grounding/citation status) the model produces a structured JSON
response useful for SnapInsight product intelligence.

Output schema (exact keys, in this order):

    {
      "normalized_category": str,
      "product_attributes": list[str],
      "nutrition_flags": list[str],
      "warning_labels": list[str],
      "caution_level": "none" | "low" | "medium" | "high",
      "suggested_questions": list[str],
      "safe_summary": str,
      "medical_claim_detected": bool
    }

Safety: ``safe_summary`` and ALL generated text must avoid medical claims
(diagnose / treat / cure / "healthy" / "safe to eat for condition" etc.),
regardless of the value of ``medical_claim_detected``.

``medical_claim_detected`` means: the SOURCE metadata (e.g. marketing copy on
the package, an ingredient blurb, an existing warning) contained a medical or
absolute-health claim that must NOT be propagated. When ``True`` the safe
summary still stays neutral and typically notes that on-package health claims
were not verified. This makes "do not overclaim" cases measurable: the model
should flag the claim AND avoid repeating it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

CAUTION_LEVELS: tuple[str, ...] = ("none", "low", "medium", "high")

# Output keys in canonical order. Used for rendering and required-field checks.
OUTPUT_FIELDS: tuple[str, ...] = (
    "normalized_category",
    "product_attributes",
    "nutrition_flags",
    "warning_labels",
    "caution_level",
    "suggested_questions",
    "safe_summary",
    "medical_claim_detected",
)

# Expected JSON types for each output field. ``list`` means list[str].
_FIELD_TYPES: dict[str, type] = {
    "normalized_category": str,
    "product_attributes": list,
    "nutrition_flags": list,
    "warning_labels": list,
    "caution_level": str,
    "suggested_questions": list,
    "safe_summary": str,
    "medical_claim_detected": bool,
}

# Input keys that an example record may carry. ``input`` is required, the rest
# are optional metadata used to build the prompt.
INPUT_FIELDS: tuple[str, ...] = (
    "product_name",
    "brand",
    "category",
    "ingredients",
    "nutrition",
    "off_fields",
    "grounding_status",
    "warnings",
    "citations",
)

# Medical-claim patterns. The tuning task must never emit these in free text.
# Mirrors the spirit of the backend eval banned patterns, scoped to this task.
MEDICAL_CLAIM_PATTERNS: tuple[str, ...] = (
    r"\bdiagnos(e|es|ed|ing|is)\b",
    r"\btreat(s|ed|ing|ment)?\b",
    r"\bcure(s|d)?\b",
    r"\bheal(s|ed|ing)?\b",
    r"\bprevents?\s+(disease|cancer|diabetes|illness)\b",
    r"\bclinically\s+proven\b",
    r"\bmedical\s+advice\b",
    r"\bdoctor\s+recommended\b",
    r"\b(is|are)\s+(healthy|unhealthy)\b",
    r"\b(safe|unsafe)\s+to\s+(eat|consume)\b",
    r"\bweight\s+loss\b",
    r"\blowers?\s+(your\s+)?(blood\s+pressure|cholesterol)\b",
)

_MEDICAL_CLAIM_REGEX = [re.compile(p, re.IGNORECASE) for p in MEDICAL_CLAIM_PATTERNS]


@dataclass
class ValidationResult:
    """Outcome of validating a single output object against the schema."""

    valid: bool
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:  # convenience for ``if result:``
        return self.valid


def detect_medical_claim(text: str) -> bool:
    """Return True if ``text`` contains a banned medical-claim pattern."""

    if not text:
        return False
    return any(rx.search(text) for rx in _MEDICAL_CLAIM_REGEX)


def find_medical_claims(text: str) -> list[str]:
    """Return the list of matched medical-claim snippets (for diagnostics)."""

    if not text:
        return []
    matches: list[str] = []
    for rx in _MEDICAL_CLAIM_REGEX:
        for m in rx.finditer(text):
            matches.append(m.group(0))
    return matches


def validate_output(obj: Any) -> ValidationResult:
    """Validate a parsed output object against the canonical schema.

    Checks: it is a dict, all required fields present, types correct, list
    fields contain only strings, ``caution_level`` is in the allowed enum, and
    ``safe_summary`` contains no medical claim while ``medical_claim_detected``
    is a bool. This does NOT mutate the object.
    """

    errors: list[str] = []

    if not isinstance(obj, dict):
        return ValidationResult(False, [f"output is not a JSON object (got {type(obj).__name__})"])

    for key in OUTPUT_FIELDS:
        if key not in obj:
            errors.append(f"missing required field: {key}")

    for key, expected_type in _FIELD_TYPES.items():
        if key not in obj:
            continue
        value = obj[key]
        # bool is a subclass of int; guard against accidental cross-typing.
        if expected_type is bool and not isinstance(value, bool):
            errors.append(f"field {key} must be bool, got {type(value).__name__}")
            continue
        if expected_type is str and not isinstance(value, str):
            errors.append(f"field {key} must be str, got {type(value).__name__}")
            continue
        if expected_type is list:
            if not isinstance(value, list):
                errors.append(f"field {key} must be a list, got {type(value).__name__}")
                continue
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    errors.append(f"field {key}[{i}] must be str, got {type(item).__name__}")

    caution = obj.get("caution_level")
    if isinstance(caution, str) and caution not in CAUTION_LEVELS:
        errors.append(
            f"caution_level {caution!r} not in {CAUTION_LEVELS}"
        )

    summary = obj.get("safe_summary")
    if isinstance(summary, str) and detect_medical_claim(summary):
        claims = find_medical_claims(summary)
        errors.append(f"safe_summary contains medical claim(s): {claims}")

    return ValidationResult(len(errors) == 0, errors)


def parse_output(raw: str) -> tuple[Any, str | None]:
    """Parse a raw model string into JSON.

    Tolerant to surrounding prose: extracts the first balanced ``{...}`` block
    if the raw text is not pure JSON. Returns ``(obj, None)`` on success or
    ``(None, error_message)`` on failure.
    """

    if raw is None:
        return None, "raw output is None"
    text = raw.strip()
    if not text:
        return None, "raw output is empty"

    # Fast path: already valid JSON.
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass

    # Strip common code fences.
    fenced = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(fenced), None
    except json.JSONDecodeError:
        pass

    # Last resort: extract first balanced brace block.
    start = fenced.find("{")
    if start == -1:
        return None, "no JSON object found in output"
    depth = 0
    for i in range(start, len(fenced)):
        ch = fenced[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = fenced[start : i + 1]
                try:
                    return json.loads(candidate), None
                except json.JSONDecodeError as exc:
                    return None, f"invalid JSON: {exc}"
    return None, "unbalanced JSON braces in output"


def canonical_output(obj: dict[str, Any]) -> dict[str, Any]:
    """Return an ordered dict containing only schema fields, in canonical order."""

    return {key: obj[key] for key in OUTPUT_FIELDS if key in obj}


def render_output_json(obj: dict[str, Any]) -> str:
    """Serialize an output object to compact, deterministic JSON for targets."""

    return json.dumps(canonical_output(obj), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Prompt construction (shared by training, eval, and Vertex export)
# ---------------------------------------------------------------------------

PROMPT_INSTRUCTION = (
    "You are SnapInsight's product-intelligence tuner. Given structured product "
    "metadata, return ONLY a JSON object with these keys: normalized_category "
    "(string), product_attributes (string list), nutrition_flags (string list), "
    "warning_labels (string list), caution_level (one of none/low/medium/high), "
    "suggested_questions (string list), safe_summary (string), "
    "medical_claim_detected (boolean). Do not make medical claims. Do not "
    "diagnose, treat, or assert that a product is healthy or unhealthy. If data "
    "is missing or uncertain, say so and raise caution_level appropriately."
)


def _format_value(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "none listed"
    if isinstance(value, dict):
        if not value:
            return "none provided"
        return "; ".join(f"{k}: {v}" for k, v in value.items())
    text = str(value).strip()
    return text if text else "unknown"


def build_prompt(record_input: dict[str, Any]) -> str:
    """Build the text prompt fed to the model from a record's ``input`` dict.

    Shared by training target construction, evaluation, and the Vertex export so
    that all paths use an identical prompt format.
    """

    lines = [PROMPT_INSTRUCTION, "", "PRODUCT METADATA:"]
    lines.append(f"- product_name: {_format_value(record_input.get('product_name'))}")
    lines.append(f"- brand: {_format_value(record_input.get('brand'))}")
    lines.append(f"- category: {_format_value(record_input.get('category'))}")
    lines.append(f"- ingredients: {_format_value(record_input.get('ingredients'))}")
    lines.append(f"- nutrition: {_format_value(record_input.get('nutrition'))}")
    lines.append(f"- off_fields: {_format_value(record_input.get('off_fields'))}")
    lines.append(
        f"- grounding_status: {_format_value(record_input.get('grounding_status'))}"
    )
    lines.append(f"- existing_warnings: {_format_value(record_input.get('warnings'))}")
    lines.append(f"- citations: {_format_value(record_input.get('citations'))}")
    lines.append("")
    lines.append("JSON:")
    return "\n".join(lines)
