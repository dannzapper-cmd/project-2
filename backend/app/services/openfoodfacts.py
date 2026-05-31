from datetime import UTC, datetime
import re
import unicodedata
from urllib.parse import quote_plus

import httpx

from app.schemas import (
    Citation,
    GroundingResult,
    NutritionSummary,
    ProductEnrichment,
    ProductSummary,
)


OPENFOODFACTS_BASE_URL = "https://world.openfoodfacts.org"
OPENFOODFACTS_TIMEOUT_SECONDS = 3.0
OPENFOODFACTS_USER_AGENT = "SnapInsight/0.1 (visual-product-companion)"
VALID_NUTRITION_GRADES = {"A", "B", "C", "D", "E"}

FIELD_LABELS = {
    "product_name": "Product Name",
    "brands": "Brand",
    "categories": "Categories",
    "ingredients_text": "Ingredients",
    "allergens_tags": "Allergens",
}


def _normalize(text: str) -> str:
    # lowercase, strip accents, strip extra whitespace
    normalized = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )
    return re.sub(r"\s+", " ", normalized)


def _safe_extract(product: dict, field: str, default: str = "") -> str:
    value = product.get(field, default)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:5])
    return str(value) if value else default


def _safe_number(product: dict, field: str) -> str | None:
    """
    Extract a numeric nutrition value and return it as a display-ready string.
    Never raises; returns None for missing, zero, or unparseable values.
    """
    raw = product.get("nutriments", {}).get(field)
    if raw is None:
        return None
    try:
        value = float(str(raw).replace(",", "."))
        if value == 0:
            return None
        return f"{value:.1f}"
    except (ValueError, TypeError):
        return None


def _normalize_tag(tag: str) -> str:
    """Convert OpenFoodFacts tag format to a display-ready label."""
    if ":" in tag:
        tag = tag.split(":", 1)[1]
    return tag.replace("-", " ").title()


def _is_specific_name(product_name: str) -> bool:
    return len(_normalize(product_name).split()) >= 3


def _product_name(product: dict) -> str:
    return _safe_extract(product, "product_name") or _safe_extract(
        product, "product_name_en"
    )


def _product_id(product: dict, fallback: str | None = None) -> str | None:
    product_id = _safe_extract(product, "code") or _safe_extract(product, "_id")
    return product_id or fallback


def _product_url(product: dict, product_id: str | None) -> str | None:
    url = _safe_extract(product, "url")
    if url:
        return url
    if product_id:
        return f"{OPENFOODFACTS_BASE_URL}/product/{product_id}"
    return None


def _category_summary(product: dict) -> str:
    categories = _safe_extract(product, "categories_tags") or _safe_extract(
        product, "categories"
    )
    return ", ".join(part.strip() for part in categories.split(",")[:3] if part.strip())


def _truncate(value: str, max_length: int = 300) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _limited_normalized_tags(product: dict, field: str, limit: int) -> list[str]:
    value = product.get(field, [])
    if not isinstance(value, list):
        return []

    labels: list[str] = []
    for raw_tag in value[:limit]:
        normalized = _normalize_tag(str(raw_tag)).strip()
        if normalized:
            labels.append(normalized)
    return labels


def _nutrition_grade(product: dict) -> str | None:
    raw_grade = _safe_extract(product, "nutrition_grades") or _safe_extract(
        product, "nutriscore_grade"
    )
    grade = raw_grade.strip().upper()
    return grade if grade in VALID_NUTRITION_GRADES else None


def _nutrition_summary(product: dict) -> NutritionSummary | None:
    summary = NutritionSummary(
        energy_kcal_100g=_safe_number(product, "energy-kcal_100g")
        or _safe_number(product, "energy-kcal"),
        sugars_100g=_safe_number(product, "sugars_100g"),
        fat_100g=_safe_number(product, "fat_100g"),
        saturated_fat_100g=_safe_number(product, "saturated-fat_100g"),
        proteins_100g=_safe_number(product, "proteins_100g"),
        salt_100g=_safe_number(product, "salt_100g"),
    )
    return summary if summary.has_any else None


def _nutrition_citation_value(summary: NutritionSummary) -> str:
    parts = []
    if summary.energy_kcal_100g:
        parts.append(f"Energy {summary.energy_kcal_100g}kcal")
    if summary.sugars_100g:
        parts.append(f"Sugars {summary.sugars_100g}g")
    if summary.fat_100g:
        parts.append(f"Fat {summary.fat_100g}g")
    if summary.saturated_fat_100g:
        parts.append(f"Saturated fat {summary.saturated_fat_100g}g")
    if summary.proteins_100g:
        parts.append(f"Protein {summary.proteins_100g}g")
    if summary.salt_100g:
        parts.append(f"Salt {summary.salt_100g}g")
    return " - ".join(parts)


def _build_base_citations(product: dict, product_id: str | None) -> list[Citation]:
    product_name = _product_name(product) or "OpenFoodFacts product"
    url = _product_url(product, product_id)
    values = {
        "product_name": product_name,
        "brands": _safe_extract(product, "brands"),
        "categories": _category_summary(product),
        "ingredients_text": _truncate(
            _safe_extract(product, "ingredients_text")
        ),
        "allergens_tags": _safe_extract(product, "allergens_tags")
        or _safe_extract(product, "allergens"),
    }

    citations: list[Citation] = []
    for field, value in values.items():
        if not value:
            continue
        citations.append(
            Citation(
                title=product_name,
                field=field,
                field_label=FIELD_LABELS[field],
                value=value,
                url=url,
            )
        )
    return citations


def _build_product_enrichment(
    product: dict, status: str, product_id: str | None
) -> tuple[ProductEnrichment | None, list[Citation]]:
    if status not in {"grounded", "partial_match"}:
        return None, []

    product_name = _product_name(product) or "OpenFoodFacts product"
    url = _product_url(product, product_id)
    nutrition_summary = _nutrition_summary(product)
    nutrition_grade = _nutrition_grade(product)
    labels = _limited_normalized_tags(product, "labels_tags", 5)
    additives = _limited_normalized_tags(product, "additives_tags", 8)

    if not any([nutrition_summary, nutrition_grade, labels, additives]):
        return None, []

    notes = [
        "Nutrition values are per 100g when available.",
        "OpenFoodFacts data is community-contributed and may be incomplete.",
    ]
    if nutrition_summary and not all(
        [
            nutrition_summary.energy_kcal_100g,
            nutrition_summary.sugars_100g,
            nutrition_summary.fat_100g,
            nutrition_summary.saturated_fat_100g,
            nutrition_summary.proteins_100g,
            nutrition_summary.salt_100g,
        ]
    ):
        notes.append("Some nutrition fields are missing from the source record.")
    if additives:
        notes.append("Additive names are sourced from OpenFoodFacts community data.")

    enrichment = ProductEnrichment(
        nutrition_summary=nutrition_summary,
        nutrition_grade=nutrition_grade,
        labels=labels,
        additives=additives,
        enrichment_source_confidence="high"
        if status == "grounded"
        else "medium",
        enrichment_notes=notes,
    )

    citations: list[Citation] = []
    if nutrition_summary:
        citations.append(
            Citation(
                title=product_name,
                field="nutriments",
                field_label="Nutrition",
                value=_nutrition_citation_value(nutrition_summary),
                url=url,
            )
        )
    if nutrition_grade:
        citations.append(
            Citation(
                title=product_name,
                field="nutrition_grades",
                field_label="Nutrition Grade",
                value=f"Nutri-Score: {nutrition_grade}",
                url=url,
            )
        )
    if labels:
        citations.append(
            Citation(
                title=product_name,
                field="labels_tags",
                field_label="Labels",
                value=" - ".join(labels[:3]),
                url=url,
            )
        )
    if additives:
        citations.append(
            Citation(
                title=product_name,
                field="additives_tags",
                field_label="Additives",
                value=" - ".join(additives[:4]),
                url=url,
            )
        )

    return enrichment, citations


def _no_match(summary: str, trace: list[str] | None = None) -> GroundingResult:
    return GroundingResult(
        grounding_status="no_match",
        grounding_summary=summary,
        match_method="none",
        source_trace=trace or [],
    )


def _unavailable(trace: list[str] | None = None) -> GroundingResult:
    return GroundingResult(
        grounding_status="grounding_unavailable",
        grounding_summary="OpenFoodFacts unavailable",
        match_method="none",
        source_trace=trace or [],
    )


class OpenFoodFactsClient:
    def __init__(
        self,
        *,
        base_url: str = OPENFOODFACTS_BASE_URL,
        timeout: float = OPENFOODFACTS_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def _get_json(
        self, path: str, params: dict[str, str] | None = None
    ) -> tuple[int, dict | None]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
            headers={"User-Agent": OPENFOODFACTS_USER_AGENT},
        ) as client:
            response = await client.get(path, params=params)
            if response.status_code == 404:
                return response.status_code, None
            if response.status_code != 200:
                return response.status_code, None
            return response.status_code, response.json()

    async def ground(self, product: ProductSummary) -> GroundingResult:
        # Contract: this method never raises. All errors produce
        # grounding_status="grounding_unavailable".
        # Privacy: OpenFoodFacts responses are not persisted beyond this request.
        try:
            return await self._ground(product)
        except (httpx.HTTPError, ValueError, TypeError):
            return _unavailable(["OpenFoodFacts request failed"])

    async def _ground(self, product: ProductSummary) -> GroundingResult:
        product_name = product.display_name.strip()
        brand = product.brand.strip() if product.brand else None
        barcode = product.barcode.strip() if product.barcode else None
        trace: list[str] = []

        if barcode:
            trace.append("barcode")
            status_code, data = await self._get_json(
                f"/api/v2/product/{quote_plus(barcode)}.json"
            )
            if status_code not in {200, 404}:
                return _unavailable(trace)
            off_product = data.get("product") if data else None
            if data and data.get("status") == 1 and isinstance(off_product, dict):
                return self._build_result(
                    product=off_product,
                    status="grounded",
                    summary="Matched by barcode",
                    match_method="barcode",
                    fallback_product_id=barcode,
                    trace=trace,
                )

        if product_name and brand:
            trace.extend(["product_name", "brand"])
            search_result = await self._search(f"{product_name} {brand}")
            if search_result is None:
                return _unavailable(trace)
            if not search_result:
                return _no_match("No reliable OpenFoodFacts match found", trace)

            top_product = search_result[0]
            off_name = _normalize(_product_name(top_product))
            off_brand = _normalize(_safe_extract(top_product, "brands"))
            if _normalize(product_name) in off_name and _normalize(brand) in off_brand:
                return self._build_result(
                    product=top_product,
                    status="partial_match",
                    summary="Matched by name and brand",
                    match_method="name_brand",
                    fallback_product_id=None,
                    trace=trace,
                )
            return _no_match("No reliable OpenFoodFacts match found", trace)

        if product_name and _is_specific_name(product_name):
            trace.append("product_name")
            search_result = await self._search(product_name)
            if search_result is None:
                return _unavailable(trace)
            if len(search_result) == 1:
                return self._build_result(
                    product=search_result[0],
                    status="partial_match",
                    summary="Matched by product name",
                    match_method="name_only",
                    fallback_product_id=None,
                    trace=trace,
                )
            return _no_match("No reliable OpenFoodFacts match found", trace)

        return _no_match(
            "Product name too generic for reliable match.",
            trace or ["product_name"],
        )

    async def _search(self, query: str) -> list[dict] | None:
        status_code, data = await self._get_json(
            "/cgi/search.pl",
            params={
                "search_terms": query,
                "json": "1",
                "page_size": "5",
            },
        )
        if status_code != 200 or data is None:
            return None
        products = data.get("products", [])
        if not isinstance(products, list):
            return None
        return [product for product in products if isinstance(product, dict)]

    def _build_result(
        self,
        *,
        product: dict,
        status: str,
        summary: str,
        match_method: str,
        fallback_product_id: str | None,
        trace: list[str],
    ) -> GroundingResult:
        product_id = _product_id(product, fallback_product_id)
        citations = _build_base_citations(product, product_id)
        product_enrichment, enrichment_citations = _build_product_enrichment(
            product, status, product_id
        )
        return GroundingResult(
            grounding_status=status,
            grounding_summary=summary,
            match_method=match_method,
            source_product_id=product_id,
            retrieved_at=datetime.now(UTC),
            citations=citations + enrichment_citations,
            source_trace=trace,
            product_enrichment=product_enrichment,
        )
