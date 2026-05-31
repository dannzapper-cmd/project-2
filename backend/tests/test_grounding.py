import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anyio
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Confidence, ProductSummary
from app.services.openfoodfacts import OpenFoodFactsClient


def post_image(client: TestClient):
    return client.post(
        "/v1/analyze/image",
        files={"file": ("product.png", b"fake image bytes", "image/png")},
    )


def make_product(
    *,
    name: str = "Organic Greek Yogurt Plain",
    brand: str | None = "Acme",
    barcode: str | None = None,
) -> ProductSummary:
    return ProductSummary(
        display_name=name,
        category="unknown",
        brand=brand,
        detected_attributes=[],
        confidence=Confidence(score=0.7, label="medium"),
        barcode=barcode,
    )


def off_product() -> dict:
    return {
        "code": "1234567890123",
        "product_name": "Organic Greek Yogurt Plain",
        "brands": "Acme",
        "categories": "Dairies, Fermented foods, Yogurts, Greek yogurts",
        "ingredients_text": "Milk, live cultures.",
        "allergens_tags": ["en:milk"],
    }


def test_barcode_match_returns_grounded():
    async def run():
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v2/product/1234567890123.json"
            return httpx.Response(200, json={"status": 1, "product": off_product()})

        client = OpenFoodFactsClient(transport=httpx.MockTransport(handler))

        result = await client.ground(make_product(barcode="1234567890123"))

        assert result.grounding_status == "grounded"
        assert result.match_method == "barcode"
        assert len(result.citations) > 0

    anyio.run(run)


def test_no_match_does_not_fail_analysis(monkeypatch):
    class FakeOpenFoodFactsClient:
        async def ground(self, product):
            def handler(_request: httpx.Request) -> httpx.Response:
                return httpx.Response(200, json={"products": []})

            return await OpenFoodFactsClient(
                transport=httpx.MockTransport(handler)
            ).ground(product)

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", raising=False)
    monkeypatch.setattr(
        "app.services.analysis_router.OpenFoodFactsClient",
        FakeOpenFoodFactsClient,
    )

    response = post_image(TestClient(app))

    assert response.status_code == 200
    body = response.json()
    assert body["grounding_status"] == "no_match"
    assert body["product"]["display_name"]
    assert body["status"] == "completed"


def test_off_timeout_returns_grounding_unavailable(monkeypatch):
    class FakeOpenFoodFactsClient:
        async def ground(self, product):
            def handler(_request: httpx.Request) -> httpx.Response:
                raise httpx.TimeoutException("timeout")

            return await OpenFoodFactsClient(
                transport=httpx.MockTransport(handler)
            ).ground(product)

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", raising=False)
    monkeypatch.setattr(
        "app.services.analysis_router.OpenFoodFactsClient",
        FakeOpenFoodFactsClient,
    )

    response = post_image(TestClient(app))

    assert response.status_code == 200
    body = response.json()
    assert body["grounding_status"] == "grounding_unavailable"
    assert body["product"]["display_name"]
    assert body["status"] == "completed"


def test_name_brand_match_returns_partial_match():
    async def run():
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/cgi/search.pl"
            return httpx.Response(200, json={"products": [off_product()]})

        client = OpenFoodFactsClient(transport=httpx.MockTransport(handler))

        result = await client.ground(make_product())

        assert result.grounding_status == "partial_match"
        assert result.match_method == "name_brand"
        assert result.citations

    anyio.run(run)


def test_generic_name_no_brand_skips_off():
    async def run():
        calls = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={"products": [off_product()]})

        client = OpenFoodFactsClient(transport=httpx.MockTransport(handler))

        result = await client.ground(make_product(name="chocolate bar", brand=None))

        assert calls == 0
        assert result.grounding_status == "no_match"

    anyio.run(run)
