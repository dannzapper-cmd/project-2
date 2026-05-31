import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.services.llmops import LLMOpsStatus, llmops


GEMINI_SECRET = "test-gemini-secret-key"
ACCESS_CODE = "live-access-secret"
TOKEN_VALUE = "ephemeral-token-value"


class ExplodingLangfuseClient:
    def trace(self, **_kwargs):
        raise RuntimeError("langfuse unavailable")


def test_live_disabled_config_and_token_fail_safely(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_GEMINI_LIVE_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", GEMINI_SECRET)

    client = TestClient(app)
    config = client.get("/v1/live/config")
    token = client.post("/v1/live/token", json={})

    assert config.status_code == 200
    assert config.json()["enabled"] is False
    assert config.json()["configured"] is False
    assert config.json()["status"] == "disabled"
    assert token.status_code == 403
    assert token.json()["status"] == "disabled"
    assert GEMINI_SECRET not in config.text + token.text


def test_live_missing_gemini_key_reports_not_configured(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_GEMINI_LIVE_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    client = TestClient(app)
    config = client.get("/v1/live/config")
    token = client.post("/v1/live/token", json={})

    assert config.status_code == 200
    assert config.json()["enabled"] is True
    assert config.json()["configured"] is False
    assert config.json()["status"] == "not_configured"
    assert token.status_code == 503
    assert token.json()["status"] == "not_configured"


def test_live_access_code_required_and_wrong_code_rejected(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_GEMINI_LIVE_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", GEMINI_SECRET)
    monkeypatch.setenv("SNAPINSIGHT_LIVE_ACCESS_CODE", ACCESS_CODE)

    client = TestClient(app)
    missing = client.post("/v1/live/token", json={})
    wrong = client.post("/v1/live/token", json={"access_code": "wrong"})

    assert missing.status_code == 403
    assert missing.json()["status"] == "access_denied"
    assert wrong.status_code == 403
    assert wrong.json()["status"] == "access_denied"
    assert ACCESS_CODE not in missing.text + wrong.text


def test_live_token_uses_v1alpha_constraints_and_exposes_no_secrets(monkeypatch):
    captured = {}

    class FakeAuthTokens:
        def create(self, *, config=None):
            captured["config"] = config
            return type("Token", (), {"name": TOKEN_VALUE})()

    class FakeClient:
        def __init__(self, *, api_key, http_options=None):
            captured["api_key"] = api_key
            captured["http_options"] = http_options
            self.auth_tokens = FakeAuthTokens()

    monkeypatch.setenv("SNAPINSIGHT_GEMINI_LIVE_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", GEMINI_SECRET)
    monkeypatch.setenv("SNAPINSIGHT_LIVE_ACCESS_CODE", ACCESS_CODE)
    monkeypatch.setenv("SNAPINSIGHT_LIVE_MAX_SESSION_SECONDS", "120")
    monkeypatch.setattr("google.genai.Client", FakeClient)

    response = TestClient(app).post(
        "/v1/live/token",
        json={"access_code": ACCESS_CODE},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["token"] == TOKEN_VALUE
    assert (
        body["websocket_url"]
        == "wss://generativelanguage.googleapis.com/ws/"
        "google.ai.generativelanguage.v1alpha.GenerativeService."
        "BidiGenerateContentConstrained"
    )
    assert body["expires_in_seconds"] == 90
    assert body["modality"] == "audio_with_transcription"

    serialized = response.text
    assert GEMINI_SECRET not in serialized
    assert ACCESS_CODE not in serialized
    assert "GEMINI_API_KEY" not in serialized

    assert captured["api_key"] == GEMINI_SECRET
    assert captured["http_options"] == {"api_version": "v1alpha"}
    config = captured["config"]
    assert getattr(config, "uses") == 1
    assert getattr(config.http_options, "api_version") == "v1alpha"

    now = datetime.now(timezone.utc)
    new_session_delta = (config.new_session_expire_time - now).total_seconds()
    expire_delta = (config.expire_time - now).total_seconds()
    assert 80 <= new_session_delta <= 90
    assert 170 <= expire_delta <= 180

    constraints = config.live_connect_constraints
    assert constraints.model == "gemini-3.1-flash-live-preview"
    live_config = constraints.config
    assert [str(item) for item in live_config.response_modalities] in (
        ["AUDIO"],
        ["Modality.AUDIO"],
    )
    assert live_config.output_audio_transcription is not None
    assert "SnapInsight" in str(live_config.system_instruction)


def test_live_telemetry_accepts_safe_metadata_and_rejects_unsafe_fields(monkeypatch):
    recorded = []

    class RecordingLangfuseClient:
        def trace(self, *, name, metadata):
            recorded.append({"name": name, "metadata": metadata})

    monkeypatch.setattr(llmops, "refresh_from_env", lambda: None)
    llmops._status = LLMOpsStatus(
        enabled=True,
        configured=True,
        provider="langfuse",
        environment="test",
    )
    llmops._client = RecordingLangfuseClient()

    client = TestClient(app)
    safe = client.post(
        "/v1/live/telemetry",
        json={
            "event": "live_session_ended",
            "duration_seconds": 42,
            "frames_sent_count": 3,
            "audio_enabled": True,
            "vision_enabled": True,
            "text_messages_count": 2,
            "model": "gemini-3.1-flash-live-preview",
            "status": "ended",
        },
    )
    unsafe = client.post(
        "/v1/live/telemetry",
        json={
            "event": "live_session_error",
            "transcript": "private spoken text",
        },
    )

    assert safe.status_code == 200
    assert safe.json()["status"] == "accepted"
    assert unsafe.status_code == 422
    assert recorded
    metadata = recorded[-1]["metadata"]
    assert metadata["route"] == "/v1/live/telemetry"
    assert metadata["live_event"] == "live_session_ended"
    assert metadata["duration_seconds"] == 42
    assert metadata["frames_sent_count"] == 3
    assert metadata["text_messages_count"] == 2
    assert "private spoken text" not in json.dumps(recorded)
    assert "transcript" not in json.dumps(recorded)


def test_live_health_and_metrics_expose_no_secrets(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_GEMINI_LIVE_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", GEMINI_SECRET)
    monkeypatch.setenv("SNAPINSIGHT_LIVE_ACCESS_CODE", ACCESS_CODE)

    client = TestClient(app)
    health = client.get("/health")
    metrics = client.get("/v1/metrics/summary")

    assert health.status_code == 200
    assert metrics.status_code == 200
    for body in [health.json(), metrics.json()]:
        assert body["gemini_live_enabled"] is True
        assert body["gemini_live_configured"] is True
        assert body["gemini_live_provider"] == "gemini_live"
        assert body["gemini_live_model"] == "gemini-3.1-flash-live-preview"

    combined = health.text + metrics.text
    assert GEMINI_SECRET not in combined
    assert ACCESS_CODE not in combined
    assert "SNAPINSIGHT_LIVE_ACCESS_CODE" not in combined


def test_langfuse_errors_do_not_break_live_telemetry(monkeypatch):
    monkeypatch.setattr(llmops, "refresh_from_env", lambda: None)
    llmops._status = LLMOpsStatus(
        enabled=True,
        configured=True,
        provider="langfuse",
        environment="test",
    )
    llmops._client = ExplodingLangfuseClient()

    response = TestClient(app).post(
        "/v1/live/telemetry",
        json={"event": "live_session_started", "status": "started"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
