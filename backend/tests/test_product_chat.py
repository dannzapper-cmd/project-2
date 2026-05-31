import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.services.product_chat import GeminiChatError


def analysis_context():
    return {
        "request_id": "analysis-request",
        "mode": "gemini",
        "status": "completed",
        "product": {
            "display_name": "Organic Greek Yogurt Plain",
            "category": "yogurt",
            "brand": "Acme",
            "detected_attributes": ["front label visible"],
            "confidence": {"score": 0.82, "label": "high"},
            "barcode": "1234567890123",
        },
        "insights": [
            {
                "title": "Visible label",
                "body": "The front label is readable.",
                "type": "observation",
            }
        ],
        "warnings": [],
        "citations": [
            {
                "source": "OpenFoodFacts",
                "title": "Organic Greek Yogurt Plain",
                "field": "ingredients_text",
                "field_label": "Ingredients",
                "value": "Milk, live cultures.",
                "url": "https://world.openfoodfacts.org/product/1234567890123",
            },
            {
                "source": "OpenFoodFacts",
                "title": "Organic Greek Yogurt Plain",
                "field": "nutriments",
                "field_label": "Nutrition",
                "value": "Energy 90.0kcal - Protein 9.0g",
                "url": "https://world.openfoodfacts.org/product/1234567890123",
            },
            {
                "source": "OpenFoodFacts",
                "title": "Organic Greek Yogurt Plain",
                "field": "labels_tags",
                "field_label": "Labels",
                "value": "Organic",
                "url": "https://world.openfoodfacts.org/product/1234567890123",
            },
        ],
        "next_questions": [],
        "privacy": {"image_stored": False, "image_retention": "none"},
        "meta": {"model": "gemini-2.5-flash", "latency_ms": 123, "api_version": "v1"},
        "grounding_status": "grounded",
        "grounding_summary": "Matched by barcode",
        "match_method": "barcode",
        "source_product_id": "1234567890123",
        "retrieved_at": None,
        "source_trace": ["barcode"],
        "product_enrichment": {
            "nutrition_summary": {
                "energy_kcal_100g": "90.0",
                "sugars_100g": "4.0",
                "fat_100g": None,
                "saturated_fat_100g": None,
                "proteins_100g": "9.0",
                "salt_100g": None,
            },
            "nutrition_grade": "B",
            "labels": ["Organic"],
            "additives": [],
            "enrichment_source_confidence": "high",
            "enrichment_notes": [
                "Nutrition values are per 100g when available.",
                "OpenFoodFacts data is community-contributed and may be incomplete.",
            ],
        },
    }


def post_chat(question: str, analysis=None, messages=None):
    return TestClient(app).post(
        "/v1/chat/product",
        json={
            "analysis": analysis or analysis_context(),
            "messages": messages or [],
            "question": question,
        },
    )


def test_chat_empty_question_returns_400(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")

    response = post_chat("   ")

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "empty_question"
    assert body["mode"] == "error"


def test_mock_chat_returns_answer(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")

    response = post_chat("What should I check?")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["answer"]


def test_gemini_chat_failure_fallback_disabled_returns_503(monkeypatch):
    async def fail_chat(**_kwargs):
        raise GeminiChatError("forced")

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", "false")
    monkeypatch.setattr("app.services.product_chat._gemini_chat_answer", fail_chat)

    response = post_chat("Explain the nutrition info simply")

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "gemini_chat_unavailable"
    assert body["mode"] == "error"


def test_gemini_chat_failure_fallback_enabled_returns_mock_fallback(monkeypatch):
    async def fail_chat(**_kwargs):
        raise GeminiChatError("forced")

    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SNAPINSIGHT_ALLOW_MOCK_FALLBACK", "true")
    monkeypatch.setattr("app.services.product_chat._gemini_chat_answer", fail_chat)

    response = post_chat("Explain the nutrition info simply")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock_fallback"
    assert "Gemini chat unavailable. Showing mock response." in body["warnings"]


def test_chat_does_not_require_or_send_image_bytes(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    payload = analysis_context()
    assert "image" not in payload
    assert "image_bytes" not in payload

    response = post_chat("Any allergens listed?", analysis=payload)

    assert response.status_code == 200
    assert response.json()["answer"]


def test_citations_used_are_subset_of_existing_citations(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ANALYSIS_MODE", "mock")
    analysis = analysis_context()

    response = post_chat("Explain the nutrition info simply", analysis=analysis)

    assert response.status_code == 200
    body = response.json()
    original = {(citation["field"], citation["value"]) for citation in analysis["citations"]}
    used = {(citation["field"], citation["value"]) for citation in body["citations_used"]}
    assert used
    assert used.issubset(original)
