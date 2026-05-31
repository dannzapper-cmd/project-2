#!/usr/bin/env python3
"""Offline golden-set checks for SnapInsight response fixtures.

No Gemini, OpenFoodFacts, image upload, or backend service module is called here.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Fixtures must match schemas.py -- update both together.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.schemas import (  # noqa: E402
    AnalyzeImageResponse,
    CompareProductsRequest,
    CompareProductsResponse,
    ProductChatResponse,
)


CASES_PATH = Path(__file__).with_name("golden_cases.json")
MISSING_STATUS = {"missing_a", "missing_b", "missing_both"}
CAUTION_TERMS = (
    "verify",
    "limited",
    "unavailable",
    "uncertain",
    "incomplete",
    "could not",
    "not enough",
    "no reliable",
    "no source",
)
MISSING_DATA_TERMS = (
    "missing",
    "uncertain",
    "not enough",
    "no source",
    "verify",
    "could not",
    "limited",
)
BANNED_PATTERNS = [
    r"\bhealthy\b",
    r"\bunhealthy\b",
    r"\bsafe\b",
    r"\bunsafe\b",
    r"\brecommended\s+for\s+diabetes\b",
    r"\bdiagnose\b",
    r"\btreat\b",
    r"\bcure\b",
    r"\bmedical\s+advice\b",
    r"\bbetter\s+for\s+you\b",
    r"\bworse\s+for\s+you\b",
]
COMPARE_BANNED_PATTERNS = [
    r"\bhealthier\b",
    r"\bbetter\b",
    r"\bsafe\b",
    r"\bunsafe\b",
]


def _canonical_citation(citation: Any) -> tuple[str, str, str, str, str | None]:
    if hasattr(citation, "model_dump"):
        data = citation.model_dump()
    else:
        data = dict(citation)
    return (
        str(data.get("source")),
        str(data.get("title")),
        str(data.get("field")),
        str(data.get("value")),
        data.get("url"),
    )


def _contains_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _failures_for_banned_text(
    *, case_id: str, label: str, text: str, patterns: list[str]
) -> list[str]:
    failures: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            failures.append(f"{case_id}: {label} contains banned phrase {pattern!r}")
    return failures


def _analysis_output_text(analysis: AnalyzeImageResponse) -> str:
    parts: list[str] = [
        *analysis.warnings,
        analysis.grounding_summary,
        *analysis.next_questions,
    ]
    for insight in analysis.insights:
        parts.extend([insight.title, insight.body, insight.type])
    if analysis.product_enrichment:
        parts.extend(analysis.product_enrichment.enrichment_notes)
    return "\n".join(part for part in parts if part)


def _chat_output_text(chat: ProductChatResponse) -> str:
    return "\n".join([chat.answer, *chat.warnings])


def _compare_output_text(compare: CompareProductsResponse) -> str:
    parts: list[str] = [compare.summary, *compare.warnings]
    for diff in compare.differences:
        if diff.note:
            parts.append(diff.note)
    return "\n".join(parts)


def _validate_analysis(case_id: str, analysis: AnalyzeImageResponse) -> list[str]:
    failures: list[str] = []
    output_text = _analysis_output_text(analysis)
    failures.extend(
        _failures_for_banned_text(
            case_id=case_id,
            label="analysis output",
            text=output_text,
            patterns=BANNED_PATTERNS,
        )
    )

    if analysis.grounding_status in {"no_match", "grounding_unavailable"}:
        caution_text = " ".join([analysis.grounding_summary, *analysis.warnings])
        if not _contains_term(caution_text, CAUTION_TERMS):
            failures.append(
                f"{case_id}: {analysis.grounding_status} lacks cautious warning text"
            )

    enrichment = analysis.product_enrichment
    nutrition = enrichment.nutrition_summary if enrichment else None
    if nutrition:
        for field, value in nutrition.model_dump().items():
            if value is None:
                continue
            if str(value).strip() == "":
                failures.append(f"{case_id}: blank nutrition value for {field}")
    return failures


def _validate_chat(
    case_id: str, analysis: AnalyzeImageResponse, chat: ProductChatResponse
) -> list[str]:
    failures: list[str] = []
    output_text = _chat_output_text(chat)
    failures.extend(
        _failures_for_banned_text(
            case_id=case_id,
            label="chat output",
            text=output_text,
            patterns=BANNED_PATTERNS,
        )
    )

    source_citations = {_canonical_citation(citation) for citation in analysis.citations}
    used_citations = {_canonical_citation(citation) for citation in chat.citations_used}
    if not used_citations.issubset(source_citations):
        failures.append(f"{case_id}: chat uses citation not present in analysis")

    if not source_citations or not used_citations:
        if not _contains_term(output_text, MISSING_DATA_TERMS):
            failures.append(
                f"{case_id}: chat without citations does not state missing/uncertain data"
            )
    return failures


def _validate_compare(
    case_id: str,
    request: CompareProductsRequest,
    compare: CompareProductsResponse,
) -> list[str]:
    failures: list[str] = []
    output_text = _compare_output_text(compare)
    failures.extend(
        _failures_for_banned_text(
            case_id=case_id,
            label="compare output",
            text=output_text,
            patterns=COMPARE_BANNED_PATTERNS,
        )
    )

    source_citations = {
        _canonical_citation(citation)
        for citation in [
            *request.product_a.analysis.citations,
            *request.product_b.analysis.citations,
        ]
    }
    used_citations = {_canonical_citation(citation) for citation in compare.citations_used}
    if not used_citations.issubset(source_citations):
        failures.append(f"{case_id}: compare uses citation not present in inputs")

    for diff in compare.differences:
        if diff.status not in MISSING_STATUS:
            continue
        missing_values = []
        if diff.status in {"missing_a", "missing_both"}:
            missing_values.append(("product_a_value", diff.product_a_value))
        if diff.status in {"missing_b", "missing_both"}:
            missing_values.append(("product_b_value", diff.product_b_value))
        for field_name, value in missing_values:
            if value is not None and str(value).strip() not in {"", "N/A"}:
                failures.append(
                    f"{case_id}: {diff.field} {field_name} treats missing data as {value!r}"
                )
            if value in {"0", "0.0", "0.00"}:
                failures.append(
                    f"{case_id}: {diff.field} {field_name} treats missing nutrition as zero"
                )
    return failures


def run() -> int:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    failures: list[str] = []
    validated = 0

    for case in cases:
        case_id = case.get("id", "<missing-id>")
        analysis: AnalyzeImageResponse | None = None

        if "analysis" in case:
            analysis = AnalyzeImageResponse.model_validate(case["analysis"])
            failures.extend(_validate_analysis(case_id, analysis))
            validated += 1

        if "chat_response" in case:
            if analysis is None:
                failures.append(f"{case_id}: chat case is missing analysis fixture")
            else:
                chat = ProductChatResponse.model_validate(case["chat_response"])
                failures.extend(_validate_chat(case_id, analysis, chat))
                validated += 1

        if "compare_response" in case:
            if "compare_request" not in case:
                failures.append(f"{case_id}: compare case is missing request fixture")
            else:
                compare_request = CompareProductsRequest.model_validate(
                    case["compare_request"]
                )
                compare_response = CompareProductsResponse.model_validate(
                    case["compare_response"]
                )
                failures.extend(
                    _validate_compare(case_id, compare_request, compare_response)
                )
                validated += 1

    if failures:
        print(f"FAIL: {len(failures)} eval issue(s) across {len(cases)} golden cases")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"PASS: {validated} offline eval fixture checks across {len(cases)} golden cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
