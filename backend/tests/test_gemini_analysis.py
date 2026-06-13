import logging

import anyio
import pytest

from app.config import Settings
from app.services.gemini_analysis import (
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MAX_PARSE_ATTEMPTS,
    INVALID_STRUCTURED_JSON_SAFE_MESSAGE,
    GeminiAnalysisError,
    analyze_image_with_gemini,
)


VALID_GEMINI_JSON = """
{
  "product": {
    "display_name": "Test Candy Bar",
    "category": "Candy",
    "brand": "Test Brand",
    "detected_attributes": ["wrapped"],
    "confidence": {"score": 0.82, "label": "high"},
    "barcode": null
  },
  "insights": [
    {
      "title": "Visible label",
      "body": "The package label is readable.",
      "type": "observation"
    }
  ],
  "warnings": ["Verify details against the physical label."],
  "next_questions": ["Would you like ingredient context?"]
}
"""

TRUNCATED_GEMINI_JSON = '{\n  "product": {\n    "display_name": "Test'


def build_settings(api_key: str = "test-live-key") -> Settings:
    return Settings(
        gemini_api_key=api_key,
        gemini_model="gemini-test-model",
        analysis_mode="gemini",
        mock_fallback_allowed=False,
        cache_enabled=False,
        cache_ttl_seconds=900,
        cache_max_entries=50,
        max_image_mb=8,
        max_analyses_per_session=5,
        max_chat_messages_per_session=10,
        max_compare_per_session=3,
        daily_analysis_limit=100,
        daily_cost_limit_usd=5.0,
        graph_enabled=False,
        neo4j_uri=None,
        neo4j_username=None,
        neo4j_password=None,
    )


class FakeGeminiResponse:
    def __init__(self, text: str | None = None):
        self.text = text


class FakeModels:
    def __init__(self, outcomes: list[object]):
        self.outcomes = outcomes
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, *, models: FakeModels, expected_api_key: str):
        self.models = models
        self.expected_api_key = expected_api_key

    def __call__(self, api_key: str):
        assert api_key == self.expected_api_key
        return self


async def run_analysis(settings: Settings):
    return await analyze_image_with_gemini(
        request_id="test-request-id",
        image_bytes=b"fake image bytes",
        content_type="image/png",
        settings=settings,
        latency_ms=12,
        api_version="v1",
    )


def test_truncated_json_first_response_retries_and_returns_valid_response(monkeypatch):
    models = FakeModels(
        [
            FakeGeminiResponse(TRUNCATED_GEMINI_JSON),
            FakeGeminiResponse(f"```json\n{VALID_GEMINI_JSON}\n```"),
        ]
    )
    settings = build_settings()
    monkeypatch.setattr(
        "app.services.gemini_analysis.genai.Client",
        FakeClient(models=models, expected_api_key=settings.gemini_api_key),
    )

    response = anyio.run(run_analysis, settings)

    assert response.status == "completed"
    assert response.mode == "gemini"
    assert response.product.display_name == "Test Candy Bar"
    assert response.product.category == "Candy"
    assert len(models.calls) == 2


def test_max_output_tokens_is_4096(monkeypatch):
    models = FakeModels([FakeGeminiResponse(VALID_GEMINI_JSON)])
    settings = build_settings()
    monkeypatch.setattr(
        "app.services.gemini_analysis.genai.Client",
        FakeClient(models=models, expected_api_key=settings.gemini_api_key),
    )

    anyio.run(run_analysis, settings)

    config = models.calls[0]["config"]
    assert config.max_output_tokens == GEMINI_MAX_OUTPUT_TOKENS == 4096


def test_invalid_json_after_retries_raises_safe_gemini_error(monkeypatch):
    models = FakeModels(
        [FakeGeminiResponse(TRUNCATED_GEMINI_JSON)]
        * GEMINI_MAX_PARSE_ATTEMPTS
    )
    settings = build_settings()
    monkeypatch.setattr(
        "app.services.gemini_analysis.genai.Client",
        FakeClient(models=models, expected_api_key=settings.gemini_api_key),
    )

    with pytest.raises(GeminiAnalysisError) as exc_info:
        anyio.run(run_analysis, settings)

    assert exc_info.value.error_class == "InvalidGeminiStructuredJson"
    assert exc_info.value.safe_message == INVALID_STRUCTURED_JSON_SAFE_MESSAGE
    assert len(models.calls) == GEMINI_MAX_PARSE_ATTEMPTS


def test_provider_status_error_does_not_retry(monkeypatch):
    class FakeProviderError(Exception):
        def __init__(self):
            super().__init__("permission denied")
            self.code = "PERMISSION_DENIED"
            self.response = type("Response", (), {"status_code": 403})()

    provider_error = FakeProviderError()
    models = FakeModels([provider_error])
    settings = build_settings()
    monkeypatch.setattr(
        "app.services.gemini_analysis.genai.Client",
        FakeClient(models=models, expected_api_key=settings.gemini_api_key),
    )

    with pytest.raises(GeminiAnalysisError) as exc_info:
        anyio.run(run_analysis, settings)

    assert len(models.calls) == 1
    assert exc_info.value.error_class == "FakeProviderError"
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "PERMISSION_DENIED"


def test_retry_logs_exclude_secrets_and_image_bytes(monkeypatch, caplog):
    api_key = "test-live-key"
    base64_blob = "A" * 120
    models = FakeModels(
        [
            FakeGeminiResponse(
                "not json "
                f"api_key={api_key} "
                "image_bytes=b'fake image bytes' "
                f"data:image/png;base64,{base64_blob}"
            ),
            FakeGeminiResponse(VALID_GEMINI_JSON),
        ]
    )
    settings = build_settings(api_key=api_key)
    monkeypatch.setattr(
        "app.services.gemini_analysis.genai.Client",
        FakeClient(models=models, expected_api_key=api_key),
    )

    with caplog.at_level(logging.WARNING, logger="app.services.gemini_analysis"):
        response = anyio.run(run_analysis, settings)

    assert response.status == "completed"
    retry_records = [
        record
        for record in caplog.records
        if record.getMessage().startswith("Gemini structured JSON parse failed")
    ]
    assert len(retry_records) == 1
    assert retry_records[0].request_id == "test-request-id"
    assert retry_records[0].model == settings.gemini_model
    assert retry_records[0].attempt == 1
    assert retry_records[0].error_class == "ValidationError"

    rendered_logs = caplog.text
    assert api_key not in rendered_logs
    assert "fake image bytes" not in rendered_logs
    assert "data:image" not in rendered_logs
    assert base64_blob not in rendered_logs
