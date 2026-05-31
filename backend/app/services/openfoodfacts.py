from datetime import UTC, datetime
import re
import unicodedata
from urllib.parse import quote_plus

import httpx

from app.schemas import Citation, GroundingResult, ProductSummary


OPENFOODFACTS_BASE_URL = "https://world.openfoodfacts.org"
OPENFOODFACTS_TIMEOUT_SECONDS = 3.0
OPENFOODFACTS_USER_AGENT = "SnapInsight/0.1 (visual-product-companion)"

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


def _build_citations(product: dict, product_id: str | None) -> list[Citation]:
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
        # Privacy: OpenFoodFacts responses are not persisted.
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
        return GroundingResult(
            grounding_status=status,
            grounding_summary=summary,
            match_method=match_method,
            source_product_id=product_id,
            retrieved_at=datetime.now(UTC),
            citations=_build_citations(product, product_id),
            source_trace=trace,
        )
