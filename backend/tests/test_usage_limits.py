import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import GroundingResult


SESSION_HEADER = "X-SnapInsight-Session-Id"
TEST_SESSION = "test-session-12345678"


def post_image(client: TestClient, session_id: str = TEST_SESSION):
    return client.post(
        "/v1/analyze/image",
        headers={SESSION_HEADER: session_id},
        files={"file": ("product.png", b"fake image bytes", "image/png")},
    )


def test_session_analysis_limit_returns_429(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.setenv("SNAPINSIGHT_MAX_ANALYSES_PER_SESSION", "2")

    client = TestClient(app)
    assert post_image(client).status_code == 200
    assert post_image(client).status_code == 200

    response = post_image(client)
    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "session_analysis_limit"
    assert body["mode"] == "error"
    assert "public demo" in body["message"].lower()


def test_daily_analysis_limit_returns_429(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.setenv("SNAPINSIGHT_DAILY_ANALYSIS_LIMIT", "2")

    client = TestClient(app)
    assert post_image(client, session_id="daily-session-aaaaaaaa").status_code == 200
    assert post_image(client, session_id="daily-session-bbbbbbbb").status_code == 200

    response = post_image(client, session_id="daily-session-cccccccc")
    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "daily_analysis_limit"


def test_session_chat_limit_returns_429(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.setenv("SNAPINSIGHT_MAX_CHAT_MESSAGES_PER_SESSION", "1")

    analysis = post_image(client := TestClient(app)).json()
    chat_payload = {
        "analysis": analysis,
        "messages": [],
        "question": "What are the ingredients?",
    }

    first = client.post(
        "/v1/chat/product",
        headers={SESSION_HEADER: TEST_SESSION},
        json=chat_payload,
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/chat/product",
        headers={SESSION_HEADER: TEST_SESSION},
        json=chat_payload,
    )
    assert second.status_code == 429
    body = second.json()
    assert body["error"] == "session_chat_limit"


def test_session_compare_limit_returns_429(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.setenv("SNAPINSIGHT_MAX_COMPARE_PER_SESSION", "1")

    analysis = post_image(client := TestClient(app)).json()
    compare_payload = {
        "product_a": {"label": "A", "analysis": analysis},
        "product_b": {"label": "B", "analysis": analysis},
    }

    first = client.post(
        "/v1/compare/products",
        headers={SESSION_HEADER: TEST_SESSION},
        json=compare_payload,
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/compare/products",
        headers={SESSION_HEADER: TEST_SESSION},
        json=compare_payload,
    )
    assert second.status_code == 429
    body = second.json()
    assert body["error"] == "session_compare_limit"


def test_daily_cost_limit_blocks_gemini_analysis(monkeypatch):
    async def fake_gemini_analysis(**_kwargs):
        from app.schemas import AnalyzeImageResponse, Confidence, PrivacySummary, ProductSummary, ResponseMeta

        return AnalyzeImageResponse(
            request_id="req",
            mode="gemini",
            status="completed",
            product=ProductSummary(
                display_name="Test Product",
                category="food",
                brand="Brand",
                detected_attributes=["packaged"],
                confidence=Confidence(score=0.8, label="high"),
                barcode=None,
            ),
            insights=[],
            warnings=[],
            citations=[],
            next_questions=[],
            privacy=PrivacySummary(image_stored=False, image_retention="ephemeral"),
            meta=ResponseMeta(model="gemini-2.5-flash", latency_ms=1, api_version="v1"),
            grounding_status="no_match",
            grounding_summary="No match",
            match_method="none",
            source_product_id=None,
            retrieved_at=None,
            source_trace=[],
            product_enrichment=None,
        )

    class FakeOpenFoodFactsClient:
        async def ground(self, product):
            return GroundingResult(
                grounding_status="no_match",
                grounding_summary="No reliable OpenFoodFacts match found",
                match_method="none",
                source_product_id=None,
                retrieved_at=None,
                citations=[],
                source_trace=["test"],
                product_enrichment=None,
            )

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", "false")
    monkeypatch.setenv("SNAPINSIGHT_DAILY_COST_LIMIT_USD", "0.001")
    monkeypatch.setattr(
        "app.services.analysis_router.analyze_image_with_gemini",
        fake_gemini_analysis,
    )
    monkeypatch.setattr(
        "app.services.analysis_router.OpenFoodFactsClient",
        FakeOpenFoodFactsClient,
    )

    response = post_image(TestClient(app))
    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "daily_cost_limit"


def test_metrics_summary_includes_usage_limits(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.setenv("SNAPINSIGHT_MAX_ANALYSES_PER_SESSION", "5")

    response = TestClient(app).get("/v1/metrics/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["usage_limits_storage"] == "in_memory"
    assert body["usage_limits_max_analyses_per_session"] == 5
    assert body["usage_limits_daily_analysis_limit"] == 100
