import time
from collections.abc import Iterable

from app.schemas import (
    AnalyzeImageResponse,
    Citation,
    CompareFieldDiff,
    CompareProductsRequest,
    CompareProductsResponse,
    NutritionSummary,
    ProductEnrichment,
)


SUMMARY = (
    "Compared using available label and OpenFoodFacts data. Some fields may be "
    "missing or community-contributed. Verify with the physical label."
)
NUTRITION_FIELDS = [
    ("energy_kcal_100g", "Energy per 100g", "kcal"),
    ("sugars_100g", "Sugars per 100g", "g"),
    ("fat_100g", "Fat per 100g", "g"),
    ("saturated_fat_100g", "Saturated fat per 100g", "g"),
    ("proteins_100g", "Protein per 100g", "g"),
    ("salt_100g", "Salt per 100g", "g"),
]
NUTRITION_CITATION_FIELDS = {
    "energy_kcal_100g",
    "sugars_100g",
    "fat_100g",
    "saturated_fat_100g",
    "proteins_100g",
    "salt_100g",
    "nutrition_grade",
}


class ProductCompareError(Exception):
    def __init__(
        self,
        *,
        error: str,
        message: str,
        status_code: int = 400,
        latency_ms: int = 0,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.status_code = status_code
        self.latency_ms = latency_ms


def _latency_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _format_list(values: list[str]) -> str | None:
    return ", ".join(values) if values else None


def _nutrition_value(
    summary: NutritionSummary | None, field: str
) -> str | None:
    if summary is None:
        return None
    value = getattr(summary, field)
    return value if not _blank(value) else None


def _enrichment_has_data(enrichment: ProductEnrichment | None) -> bool:
    if enrichment is None:
        return False
    summary = enrichment.nutrition_summary
    return any(
        [
            summary.has_any if summary else False,
            enrichment.nutrition_grade,
            enrichment.labels,
            enrichment.additives,
        ]
    )


def _has_minimum_compare_data(analysis: AnalyzeImageResponse) -> bool:
    product = analysis.product
    has_identity = any([product.display_name.strip(), product.brand, product.category.strip()])
    has_grounding = analysis.grounding_status in {
        "grounded",
        "partial_match",
        "grounding_unavailable",
    } or analysis.match_method not in {None, "none"}
    return has_identity or has_grounding or _enrichment_has_data(analysis.product_enrichment)


def _compare_value(a: str | None, b: str | None) -> str:
    if _blank(a) and _blank(b):
        return "missing_both"
    if _blank(a):
        return "missing_a"
    if _blank(b):
        return "missing_b"
    return "same" if a == b else "different"


def _parse_float(value: str | None) -> float | None:
    if _blank(value):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _compare_numeric(a: str | None, b: str | None) -> str:
    # Returns "same", "different", "missing_a", "missing_b",
    # or "missing_both". Never raises.
    if _blank(a) and _blank(b):
        return "missing_both"
    if _blank(a):
        return "missing_a"
    if _blank(b):
        return "missing_b"

    parsed_a = _parse_float(a)
    parsed_b = _parse_float(b)
    if parsed_a is not None and parsed_b is not None:
        return "same" if round(parsed_a, 1) == round(parsed_b, 1) else "different"
    return "same" if a == b else "different"


def _numeric_note(
    a: str | None, b: str | None, unit: str, status: str
) -> str | None:
    if status != "different":
        return None
    parsed_a = _parse_float(a)
    parsed_b = _parse_float(b)
    if parsed_a is None or parsed_b is None:
        return None
    return (
        f"Product A: {round(parsed_a, 1)}{unit} · "
        f"Product B: {round(parsed_b, 1)}{unit} (per 100g, source data)"
    )


def _diff(
    *,
    field: str,
    label: str,
    product_a_value: str | None,
    product_b_value: str | None,
    status: str | None = None,
    note: str | None = None,
) -> CompareFieldDiff:
    return CompareFieldDiff(
        field=field,
        label=label,
        product_a_value=product_a_value,
        product_b_value=product_b_value,
        status=status or _compare_value(product_a_value, product_b_value),  # type: ignore[arg-type]
        note=note,
    )


def _citations_for_fields(field: str) -> set[str]:
    if field in NUTRITION_CITATION_FIELDS:
        return {"nutriments", "nutrition_grades"}
    if field == "labels":
        return {"labels_tags"}
    if field == "additives":
        return {"additives_tags"}
    if field == "allergens":
        return {"allergens_tags"}
    return set()


def _dedupe_citations(citations: Iterable[Citation]) -> list[Citation]:
    seen: set[tuple[str, str, str | None]] = set()
    deduped: list[Citation] = []
    for citation in citations:
        key = (citation.source, citation.field, citation.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def citations_used_for_differences(
    differences: list[CompareFieldDiff],
    product_a: AnalyzeImageResponse,
    product_b: AnalyzeImageResponse,
) -> list[Citation]:
    # Deterministic citation selection, consistent with chat PR.
    fields: set[str] = set()
    for difference in differences:
        if difference.status == "missing_both":
            continue
        fields.update(_citations_for_fields(difference.field))
    if not fields:
        return []
    return _dedupe_citations(
        citation
        for citation in [*product_a.citations, *product_b.citations]
        if citation.field in fields
    )


def compare_products(
    *,
    request: CompareProductsRequest,
    request_id: str,
    started_at: float,
) -> CompareProductsResponse:
    product_a = request.product_a.analysis
    product_b = request.product_b.analysis

    if not (
        _has_minimum_compare_data(product_a)
        or _has_minimum_compare_data(product_b)
    ):
        raise ProductCompareError(
            error="compare_insufficient_data",
            message="Neither product has enough data to compare.",
            status_code=400,
            latency_ms=_latency_ms(started_at),
        )

    enrichment_a = product_a.product_enrichment
    enrichment_b = product_b.product_enrichment
    nutrition_a = enrichment_a.nutrition_summary if enrichment_a else None
    nutrition_b = enrichment_b.nutrition_summary if enrichment_b else None
    differences: list[CompareFieldDiff] = [
        _diff(
            field="product_name",
            label="Product name",
            product_a_value=product_a.product.display_name or None,
            product_b_value=product_b.product.display_name or None,
        ),
        _diff(
            field="brand",
            label="Brand",
            product_a_value=product_a.product.brand,
            product_b_value=product_b.product.brand,
        ),
        _diff(
            field="category",
            label="Category",
            product_a_value=product_a.product.category or None,
            product_b_value=product_b.product.category or None,
        ),
        _diff(
            field="grounding_status",
            label="Grounding status",
            product_a_value=product_a.grounding_status,
            product_b_value=product_b.grounding_status,
        ),
        _diff(
            field="grounding_summary",
            label="Grounding summary",
            product_a_value=product_a.grounding_summary,
            product_b_value=product_b.grounding_summary,
        ),
        _diff(
            field="match_method",
            label="Match method",
            product_a_value=product_a.match_method,
            product_b_value=product_b.match_method,
        ),
    ]

    for field, label, unit in NUTRITION_FIELDS:
        value_a = _nutrition_value(nutrition_a, field)
        value_b = _nutrition_value(nutrition_b, field)
        status = _compare_numeric(value_a, value_b)
        differences.append(
            _diff(
                field=field,
                label=label,
                product_a_value=value_a,
                product_b_value=value_b,
                status=status,
                note=_numeric_note(value_a, value_b, unit, status),
            )
        )

    differences.extend(
        [
            _diff(
                field="nutrition_grade",
                label="Nutrition grade",
                product_a_value=enrichment_a.nutrition_grade if enrichment_a else None,
                product_b_value=enrichment_b.nutrition_grade if enrichment_b else None,
            ),
            _diff(
                field="labels",
                label="Labels",
                product_a_value=_format_list(enrichment_a.labels) if enrichment_a else None,
                product_b_value=_format_list(enrichment_b.labels) if enrichment_b else None,
            ),
            _diff(
                field="additives",
                label="Additives",
                product_a_value=_format_list(enrichment_a.additives) if enrichment_a else None,
                product_b_value=_format_list(enrichment_b.additives) if enrichment_b else None,
            ),
            _diff(
                field="warnings",
                label="Warning count",
                product_a_value=str(len(product_a.warnings)) if product_a.warnings else None,
                product_b_value=str(len(product_b.warnings)) if product_b.warnings else None,
            ),
        ]
    )

    # A compare result with all missing_both is valid output.
    # It communicates that data is unavailable, which is true.
    warnings = [
        "Analysis is based on available source data. Verify physical labels.",
    ]
    if any(
        product.grounding_status == "partial_match"
        for product in [product_a, product_b]
    ):
        warnings.append("One product was matched by name. Verify with the label.")
    if any(
        product.grounding_status in {"no_match", "grounding_unavailable"}
        for product in [product_a, product_b]
    ):
        warnings.append("Source data is limited for one product.")

    return CompareProductsResponse(
        summary=SUMMARY,
        differences=differences,
        citations_used=citations_used_for_differences(
            differences,
            product_a,
            product_b,
        ),
        warnings=warnings,
        request_id=request_id,
        latency_ms=_latency_ms(started_at),
    )
