import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import AnalyzeImageResponse
from app.services import analysis_router
from app.services.analysis_cache import analysis_cache, compute_cache_key
from app.services.gemini_analysis import GeminiAnalysisError

IMAGE_BYTES = b"fake image bytes for cache"
OTHER_IMAGE_BYTES = b"a different product image"


class FakeOpenFoodFactsClient:
    """Avoids any live OpenFoodFacts network call during tests."""

    async def ground(self, product):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"products": []})

        from app.services.openfoodfacts import OpenFoodFactsClient

        return await OpenFoodFactsClient(
            transport=httpx.MockTransport(handler)
        ).ground(product)


def use_mock_mode(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", raising=False)
    monkeypatch.setattr(
        analysis_router, "OpenFoodFactsClient", FakeOpenFoodFactsClient
    )


def post_image(client: TestClient, data: bytes = IMAGE_BYTES):
    return client.post(
        "/v1/analyze/image",
        files={"file": ("product.png", data, "image/png")},
    )


def test_analysis_cache_hit_on_repeated_image(monkeypatch):
    use_mock_mode(monkeypatch)
    monkeypatch.setenv("SNAPINSIGHT_CACHE_ENABLED", "true")

    calls = {"count": 0}
    original = analysis_router.build_mock_image_analysis_response

    def counting_builder(**kwargs):
        calls["count"] += 1
        return original(**kwargs)

    monkeypatch.setattr(
        analysis_router, "build_mock_image_analysis_response", counting_builder
    )

    client = TestClient(app)

    first = post_image(client)
    assert first.status_code == 200
    assert first.json()["cache_hit"] is False

    second = post_image(client)
    assert second.status_code == 200
    assert second.json()["cache_hit"] is True

    # Underlying analysis ran only once; the second response came from cache.
    assert calls["count"] == 1
    # Fresh request_id even on cache hits.
    assert first.json()["request_id"] != second.json()["request_id"]


def test_different_image_is_cache_miss(monkeypatch):
    use_mock_mode(monkeypatch)
    monkeypatch.setenv("SNAPINSIGHT_CACHE_ENABLED", "true")

    client = TestClient(app)

    first = post_image(client, IMAGE_BYTES)
    assert first.json()["cache_hit"] is False

    other = post_image(client, OTHER_IMAGE_BYTES)
    assert other.json()["cache_hit"] is False


def test_cache_does_not_store_errors(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", "false")
    monkeypatch.setenv("SNAPINSIGHT_CACHE_ENABLED", "true")

    async def fail_gemini_analysis(**_kwargs):
        raise GeminiAnalysisError("TimeoutError")

    monkeypatch.setattr(
        analysis_router, "analyze_image_with_gemini", fail_gemini_analysis
    )

    client = TestClient(app)

    response = post_image(client)
    assert response.status_code == 503
    assert response.json()["mode"] == "error"

    # Nothing was cached for the failing request.
    assert analysis_cache.size() == 0


def test_oversized_image_rejected(monkeypatch):
    use_mock_mode(monkeypatch)
    monkeypatch.setenv("SNAPINSIGHT_MAX_IMAGE_MB", "1")

    oversized = b"0" * (1 * 1024 * 1024 + 1)
    client = TestClient(app)

    response = post_image(client, oversized)

    assert response.status_code in {400, 413}
    body = response.json()
    detail = body.get("detail") or body.get("message")
    assert detail == "Image is too large. Please upload a smaller image."


def test_cache_can_be_disabled(monkeypatch):
    use_mock_mode(monkeypatch)
    monkeypatch.setenv("SNAPINSIGHT_CACHE_ENABLED", "false")

    client = TestClient(app)

    first = post_image(client)
    second = post_image(client)

    # When disabled, cache_hit is never True (None signals "not applicable").
    assert first.json()["cache_hit"] is None
    assert second.json()["cache_hit"] is None
    assert analysis_cache.size() == 0


def test_cache_key_does_not_expose_raw_image():
    key = compute_cache_key(
        IMAGE_BYTES, analysis_mode="mock", model_version="mock"
    )

    # Key is a SHA-256 hex digest, not the raw bytes/base64.
    assert re.fullmatch(r"[0-9a-f]{64}", key)
    assert IMAGE_BYTES.hex() not in key
    assert "fake image bytes" not in key


def test_cache_structure_stores_no_raw_image(monkeypatch):
    use_mock_mode(monkeypatch)
    monkeypatch.setenv("SNAPINSIGHT_CACHE_ENABLED", "true")

    client = TestClient(app)
    post_image(client)

    assert analysis_cache.size() == 1
    for stored_key, entry in analysis_cache._cache.items():
        assert re.fullmatch(r"[0-9a-f]{64}", stored_key)
        # The cached value is the analysis response object only.
        assert isinstance(entry.value, AnalyzeImageResponse)
        serialized = entry.value.model_dump_json()
        assert "fake image bytes for cache" not in serialized
        assert IMAGE_BYTES.hex() not in serialized


def test_metrics_summary_returns_no_user_data(monkeypatch):
    use_mock_mode(monkeypatch)

    client = TestClient(app)
    response = client.get("/v1/metrics/summary")

    assert response.status_code == 200
    body = response.json()
    counters = body["counters"]
    for name in [
        "total_analysis_requests",
        "cache_hits",
        "cache_misses",
        "gemini_requests",
        "mock_requests",
        "mock_fallbacks",
        "analysis_errors",
        "grounding_grounded",
        "grounding_partial_match",
        "grounding_no_match",
        "grounding_unavailable",
        "chat_requests",
        "compare_requests",
    ]:
        assert name in counters
        assert isinstance(counters[name], int)

    assert "uptime_seconds" in body

    # No image data, base64, prompts, chat messages, or product names leak.
    raw = response.text.lower()
    for forbidden in ["base64", "image_bytes", "data:image", "ingredients", "answer"]:
        assert forbidden not in raw


def test_metrics_update_after_analysis_chat_compare(monkeypatch):
    use_mock_mode(monkeypatch)

    client = TestClient(app)

    analysis = post_image(client).json()
    assert analysis["status"] == "completed"

    chat_response = client.post(
        "/v1/chat/product",
        json={"analysis": analysis, "messages": [], "question": "Any allergens?"},
    )
    assert chat_response.status_code == 200

    compare_response = client.post(
        "/v1/compare/products",
        json={
            "product_a": {"label": "A", "analysis": analysis},
            "product_b": {"label": "B", "analysis": analysis},
        },
    )
    assert compare_response.status_code == 200

    summary = client.get("/v1/metrics/summary").json()
    counters = summary["counters"]
    assert counters["total_analysis_requests"] == 1
    assert counters["mock_requests"] == 1
    assert counters["chat_requests"] == 1
    assert counters["compare_requests"] == 1
    assert counters["cache_misses"] == 1
