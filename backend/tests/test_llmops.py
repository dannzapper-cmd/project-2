import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import GroundingResult
from app.services import analysis_router
from app.services.llmops import LLMOpsStatus, llmops, safe_metadata


IMAGE_SECRET = "raw-image-secret-bytes"
QUESTION_SECRET = "private shopper note 123"
FILENAME_SECRET = "private-product-photo.png"


class FakeOpenFoodFactsClient:
    async def ground(self, _product):
        return GroundingResult(
            grounding_status="no_match",
            grounding_summary="No reliable OpenFoodFacts match found",
            match_method="none",
            citations=[],
            source_trace=[],
        )


class RecordingLangfuseClient:
    def __init__(self):
        self.events = []
        self.shutdown_called = False

    def trace(self, *, name, metadata):
        self.events.append({"name": name, "metadata": metadata})
        return None

    def shutdown(self):
        self.shutdown_called = True


class ExplodingLangfuseClient:
    def trace(self, **_kwargs):
        raise RuntimeError("langfuse unavailable")


def analysis_context():
    return {
        "request_id": "analysis-request",
        "mode": "mock",
        "status": "completed",
        "product": {
            "display_name": "Product image received",
            "category": "unknown",
            "brand": None,
            "detected_attributes": [],
            "confidence": {"score": 0.0, "label": "mock"},
            "barcode": None,
        },
        "insights": [],
        "warnings": ["No image was stored."],
        "citations": [],
        "next_questions": [],
        "privacy": {"image_stored": False, "image_retention": "none"},
        "meta": {"model": "mock", "latency_ms": 1, "api_version": "v1"},
        "grounding_status": "no_match",
        "grounding_summary": "No reliable OpenFoodFacts match found",
        "match_method": "none",
        "source_product_id": None,
        "retrieved_at": None,
        "source_trace": [],
        "product_enrichment": None,
        "cache_hit": False,
    }


def enable_fake_llmops(monkeypatch, client):
    monkeypatch.setattr(llmops, "refresh_from_env", lambda: None)
    llmops._status = LLMOpsStatus(
        enabled=True,
        configured=True,
        provider="langfuse",
        environment="test",
    )
    llmops._client = client


def test_llmops_disabled_no_crash(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_LLMOPS_ENABLED", "false")
    llmops.refresh_from_env()

    llmops.trace_event(
        name="test.disabled",
        metadata={
            "route": "/v1/analyze/image",
            "operation": "analyze_image",
            "raw_prompt": "do not send",
            "api_key": "do-not-send",
        },
    )

    assert llmops.status.enabled is False
    assert llmops.status.configured is False
    assert llmops.status.provider == "disabled"


def test_missing_langfuse_env_vars_no_crash_and_unconfigured(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_LLMOPS_ENABLED", "true")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)

    llmops.refresh_from_env()
    llmops.trace_event(
        name="test.missing_env",
        metadata={"route": "/health", "operation": "health"},
    )

    assert llmops.status.enabled is True
    assert llmops.status.configured is False
    assert llmops.status.provider == "langfuse"


def test_safe_metadata_filters_sensitive_and_unknown_fields():
    metadata = safe_metadata(
        {
            "route": "/v1/chat/product",
            "operation": "chat_product",
            "question_length": 24,
            "raw_user_question": "What about my private note?",
            "image_bytes": IMAGE_SECRET,
            "authorization": "Bearer secret",
            "api_key": "secret-key",
        }
    )

    serialized = json.dumps(metadata)
    assert metadata == {
        "route": "/v1/chat/product",
        "operation": "chat_product",
        "question_length": 24,
    }
    assert IMAGE_SECRET not in serialized
    assert "private note" not in serialized
    assert "secret-key" not in serialized


def test_health_and_metrics_expose_safe_llmops_status(monkeypatch):
    secret_public = "pk-test-secret"
    secret_private = "sk-test-secret"
    monkeypatch.setattr(llmops, "refresh_from_env", lambda: None)
    llmops._status = LLMOpsStatus(
        enabled=True,
        configured=True,
        provider="langfuse",
        environment="render-prod",
    )
    llmops._client = None

    client = TestClient(app)
    health = client.get("/health")
    metrics = client.get("/v1/metrics/summary")

    assert health.status_code == 200
    assert metrics.status_code == 200
    for body in [health.json(), metrics.json()]:
        assert body["llmops_enabled"] is True
        assert body["llmops_configured"] is True
        assert body["llmops_provider"] == "langfuse"
        assert body["llmops_environment"] == "render-prod"

    combined = health.text + metrics.text
    assert secret_public not in combined
    assert secret_private not in combined
    assert "LANGFUSE_SECRET_KEY" not in combined
    assert "LANGFUSE_PUBLIC_KEY" not in combined


def test_langfuse_client_error_does_not_break_endpoint(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    enable_fake_llmops(monkeypatch, ExplodingLangfuseClient())

    response = TestClient(app).post(
        "/v1/compare/products",
        json={
            "product_a": {"label": "A", "analysis": analysis_context()},
            "product_b": {"label": "B", "analysis": analysis_context()},
        },
    )

    assert response.status_code == 200
    assert response.json()["request_id"]


def test_analyze_chat_compare_tracing_uses_safe_metadata(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    monkeypatch.setenv("SNAPINSIGHT_CACHE_ENABLED", "false")
    monkeypatch.setattr(
        analysis_router,
        "OpenFoodFactsClient",
        FakeOpenFoodFactsClient,
    )
    recording_client = RecordingLangfuseClient()
    enable_fake_llmops(monkeypatch, recording_client)

    client = TestClient(app)
    analysis = client.post(
        "/v1/analyze/image",
        files={
            "file": (
                FILENAME_SECRET,
                IMAGE_SECRET.encode("utf-8"),
                "image/png",
            )
        },
    )
    assert analysis.status_code == 200
    analysis_body = analysis.json()

    chat = client.post(
        "/v1/chat/product",
        json={
            "analysis": analysis_body,
            "messages": [{"role": "user", "content": "previous private message"}],
            "question": f"Is this suitable? {QUESTION_SECRET}",
        },
    )
    assert chat.status_code == 200

    compare = client.post(
        "/v1/compare/products",
        json={
            "product_a": {"label": "A", "analysis": analysis_body},
            "product_b": {"label": "B", "analysis": analysis_body},
        },
    )
    assert compare.status_code == 200

    names = [event["name"] for event in recording_client.events]
    assert "snapinsight.analyze" in names
    assert "snapinsight.chat" in names
    assert "snapinsight.compare" in names

    by_name = {event["name"]: event["metadata"] for event in recording_client.events}
    assert by_name["snapinsight.analyze"]["route"] == "/v1/analyze/image"
    assert by_name["snapinsight.analyze"]["analysis_mode"] == "mock"
    assert by_name["snapinsight.analyze"]["cache_hit"] is None
    assert by_name["snapinsight.analyze"]["citations_count"] == 0
    assert by_name["snapinsight.chat"]["message_count"] == 1
    assert by_name["snapinsight.chat"]["question_length"] == len(
        f"Is this suitable? {QUESTION_SECRET}"
    )
    assert by_name["snapinsight.compare"]["diff_count"] > 0

    serialized_events = json.dumps(recording_client.events)
    for forbidden in [
        IMAGE_SECRET,
        FILENAME_SECRET,
        QUESTION_SECRET,
        "previous private message",
        "image_bytes",
        "base64",
        "raw_user_question",
    ]:
        assert forbidden not in serialized_events


def test_llmops_shutdown_uses_sdk_lifecycle(monkeypatch):
    recording_client = RecordingLangfuseClient()
    enable_fake_llmops(monkeypatch, recording_client)

    llmops.shutdown()

    assert recording_client.shutdown_called is True
