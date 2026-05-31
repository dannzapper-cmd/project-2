import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
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
