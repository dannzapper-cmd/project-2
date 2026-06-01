import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import GroundingResult
from app.services.gemini_analysis import GeminiAnalysisError


def post_image(client: TestClient):
    return client.post(
        "/v1/analyze/image",
        files={"file": ("product.png", b"fake image bytes", "image/png")},
    )


def test_invalid_mode_raises(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "invalid")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", raising=False)

    response = post_image(TestClient(app))

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "invalid_analysis_mode"
    assert body["mode"] == "error"
    assert (
        body["message"]
        == "Invalid SNAPINSIGHT_ANALYSIS_MODE: invalid. Accepted: mock, gemini."
    )


def test_gemini_mode_missing_key(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", raising=False)

    response = post_image(TestClient(app))

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "gemini_not_configured"
    assert body["mode"] == "error"
    assert body["message"] == "Gemini API key is not configured."
    assert body["latency_ms"] == 0
    assert body["request_id"]


def test_fallback_disabled_returns_error(monkeypatch):
    async def fail_gemini_analysis(**_kwargs):
        raise GeminiAnalysisError("TimeoutError")

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", "false")
    monkeypatch.setattr(
        "app.services.analysis_router.analyze_image_with_gemini",
        fail_gemini_analysis,
    )

    response = post_image(TestClient(app))

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "gemini_unavailable"
    assert body["mode"] == "error"
    assert (
        body["message"]
        == "Gemini analysis failed and mock fallback is disabled."
    )
    assert isinstance(body["latency_ms"], int)
    assert body["request_id"]


def test_fallback_enabled_returns_mock_fallback_without_gemini(monkeypatch):
    async def fail_gemini_analysis(**_kwargs):
        raise GeminiAnalysisError("TimeoutError")

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
    monkeypatch.setenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", "true")
    monkeypatch.setattr(
        "app.services.analysis_router.analyze_image_with_gemini",
        fail_gemini_analysis,
    )
    monkeypatch.setattr(
        "app.services.analysis_router.OpenFoodFactsClient",
        FakeOpenFoodFactsClient,
    )

    response = post_image(TestClient(app))

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock_fallback"
    assert body["status"] == "completed"
    assert body["grounding_status"] == "no_match"
    assert "Gemini unavailable. Showing mock result." in body["warnings"]
    assert body["privacy"]["image_stored"] is False


def test_gemini_analysis_error_stores_safe_details():
    error = GeminiAnalysisError(
        "BadRequestError",
        safe_message="x" * 350,
        status_code=400,
        code="invalid_argument",
    )

    assert error.error_class == "BadRequestError"
    assert error.status_code == 400
    assert error.code == "invalid_argument"
    assert error.safe_message == "x" * 300


def test_gemini_failure_logs_sanitized_details(monkeypatch, caplog):
    api_key = "test-live-key"
    model = "gemini-test-model"
    base64_blob = "A" * 120

    class FakeGeminiError(Exception):
        def __init__(self, message: str):
            super().__init__(message)
            self.code = "UNAUTHENTICATED"
            self.response = type("Response", (), {"status_code": 401})()

    class FakeModels:
        def generate_content(self, **_kwargs):
            raise FakeGeminiError(
                "Gemini auth failed with "
                f"api_key={api_key}; "
                "image_bytes=b'fake image bytes'; "
                f"payload=data:image/png;base64,{base64_blob}"
            )

    class FakeClient:
        def __init__(self, api_key: str):
            assert api_key == "test-live-key"
            self.models = FakeModels()

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", api_key)
    monkeypatch.setenv("GEMINI_MODEL", model)
    monkeypatch.setenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", "false")
    monkeypatch.setattr("app.services.gemini_analysis.genai.Client", FakeClient)

    with caplog.at_level(logging.WARNING, logger="app.services.analysis_router"):
        response = post_image(TestClient(app))

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "gemini_unavailable"
    assert body["mode"] == "error"
    assert body["message"] == "Gemini analysis failed and mock fallback is disabled."

    warning_records = [
        record
        for record in caplog.records
        if record.getMessage().startswith("Gemini analysis failed ")
    ]
    assert warning_records
    record = warning_records[-1]
    rendered_message = record.getMessage()

    assert record.request_id
    assert record.model == model
    assert record.error_class == "FakeGeminiError"
    assert record.provider_status == 401
    assert record.provider_code == "UNAUTHENTICATED"
    assert record.safe_message
    assert len(record.safe_message) <= 300

    # Render-visible message contains the useful diagnostics.
    assert "error_class=FakeGeminiError" in rendered_message
    assert "provider_status=401" in rendered_message
    assert "provider_code=UNAUTHENTICATED" in rendered_message
    assert "safe_message=" in rendered_message

    # Safe logs must never include raw API key or image payload.
    assert api_key not in record.safe_message
    assert "fake image bytes" not in record.safe_message
    assert "data:image" not in record.safe_message
    assert base64_blob not in record.safe_message
    assert api_key not in rendered_message
    assert "fake image bytes" not in rendered_message
    assert "data:image" not in rendered_message
    assert base64_blob not in rendered_message
