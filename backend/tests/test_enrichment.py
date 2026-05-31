import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anyio
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Confidence, ProductSummary
from app.services.openfoodfacts import OpenFoodFactsClient


def make_product(
    *,
    name: str = "Organic Greek Yogurt Plain",
    brand: str | None = "Acme",
    barcode: str | None = "1234567890123",
) -> ProductSummary:
    return ProductSummary(
        display_name=name,
        category="unknown",
        brand=brand,
        detected_attributes=[],
        confidence=Confidence(score=0.7, label="medium"),
        barcode=barcode,
    )


def off_product(**overrides) -> dict:
    product = {
        "code": "1234567890123",
        "product_name": "Organic Greek Yogurt Plain",
        "brands": "Acme",
        "categories": "Dairies, Fermented foods, Yogurts",
        "ingredients_text": "Milk, live cultures.",
        "allergens_tags": ["en:milk"],
        "nutriments": {
            "energy-kcal_100g": 234,
            "sugars_100g": "12,3",
            "fat_100g": 8.1,
            "saturated-fat_100g": 4.2,
            "proteins_100g": 9,
            "salt_100g": 0.2,
        },
        "nutrition_grades": "a",
        "labels_tags": ["en:organic", "en:fair-trade"],
        "additives_tags": ["en:e102", "en:e330"],
    }
    product.update(overrides)
    return product


def run_grounding(product: ProductSummary, off_payload: dict):
    async def run():
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.startswith("/api/v2/product/"):
                return httpx.Response(
                    200,
                    json={"status": 1, "product": off_payload},
                )
            return httpx.Response(200, json={"products": [off_payload]})

        client = OpenFoodFactsClient(transport=httpx.MockTransport(handler))
        return await client.ground(product)

    return anyio.run(run)


def test_enrichment_added_for_barcode_match():
    result = run_grounding(make_product(), off_product())

    assert result.product_enrichment is not None
    enrichment = result.product_enrichment
    assert enrichment.nutrition_summary is not None
    assert enrichment.nutrition_summary.energy_kcal_100g == "234.0"
    assert enrichment.nutrition_grade == "A"
    assert enrichment.labels == ["Organic", "Fair Trade"]
    assert enrichment.additives == ["E102", "E330"]
    assert enrichment.enrichment_source_confidence == "high"
    assert any(citation.field == "nutriments" for citation in result.citations)
    assert any(citation.field == "nutrition_grades" for citation in result.citations)
    assert any(citation.field == "labels_tags" for citation in result.citations)
    assert any(citation.field == "additives_tags" for citation in result.citations)


def test_no_enrichment_for_no_match(monkeypatch):
    class FakeOpenFoodFactsClient:
        async def ground(self, product):
            def handler(_request: httpx.Request) -> httpx.Response:
                return httpx.Response(200, json={"products": []})

            return await OpenFoodFactsClient(
                transport=httpx.MockTransport(handler)
            ).ground(product)

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.analysis_router.OpenFoodFactsClient",
        FakeOpenFoodFactsClient,
    )

    response = TestClient(app).post(
        "/v1/analyze/image",
        files={"file": ("product.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_enrichment"] is None
    assert body["product"]["display_name"]
    assert body["status"] == "completed"


def test_missing_nutriments_do_not_break_enrichment():
    product = off_product()
    product.pop("nutriments")

    result = run_grounding(make_product(), product)

    assert result.product_enrichment is not None
    enrichment = result.product_enrichment
    assert enrichment.nutrition_summary is None
    assert enrichment.nutrition_grade == "A"
    assert enrichment.labels == ["Organic", "Fair Trade"]


def test_grade_present_nutriments_absent():
    result = run_grounding(
        make_product(),
        off_product(nutriments={}, nutrition_grades="b", labels_tags=[], additives_tags=[]),
    )

    assert result.product_enrichment is not None
    enrichment = result.product_enrichment
    assert enrichment.nutrition_grade == "B"
    assert enrichment.nutrition_summary is None


def test_invalid_grade_value_is_discarded():
    result = run_grounding(
        make_product(),
        off_product(nutrition_grades="unknown", labels_tags=["en:organic"]),
    )

    assert result.product_enrichment is not None
    assert result.product_enrichment.nutrition_grade is None


def test_additive_label_tags_are_normalized():
    result = run_grounding(
        make_product(),
        off_product(
            additives_tags=["en:e102", "en:e330"],
            labels_tags=["en:organic", "en:fair-trade"],
        ),
    )

    assert result.product_enrichment is not None
    assert result.product_enrichment.additives == ["E102", "E330"]
    assert result.product_enrichment.labels == ["Organic", "Fair Trade"]


def test_enrichment_source_confidence_is_medium_for_partial_match():
    result = run_grounding(
        make_product(barcode=None),
        off_product(),
    )

    assert result.grounding_status == "partial_match"
    assert result.product_enrichment is not None
    assert result.product_enrichment.enrichment_source_confidence == "medium"
