import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def analysis_context(**overrides):
    base = {
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
        "insights": [],
        "warnings": [],
        "citations": [
            {
                "source": "OpenFoodFacts",
                "title": "Organic Greek Yogurt Plain",
                "field": "nutriments",
                "field_label": "Nutrition",
                "value": "Energy 90.0kcal - Sugars 4.0g",
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
            {
                "source": "OpenFoodFacts",
                "title": "Organic Greek Yogurt Plain",
                "field": "ingredients_text",
                "field_label": "Ingredients",
                "value": "Milk, live cultures.",
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
                "fat_100g": "2.0",
                "saturated_fat_100g": "1.0",
                "proteins_100g": "9.0",
                "salt_100g": "0.1",
            },
            "nutrition_grade": "B",
            "labels": ["Organic"],
            "additives": [],
            "enrichment_source_confidence": "high",
            "enrichment_notes": [],
        },
    }
    base.update(overrides)
    return base


def compare_payload(product_a=None, product_b=None):
    return {
        "product_a": {"label": "A", "analysis": product_a or analysis_context()},
        "product_b": {
            "label": "B",
            "analysis": product_b
            or analysis_context(
                request_id="analysis-request-b",
                product={
                    "display_name": "Strawberry Yogurt",
                    "category": "yogurt",
                    "brand": "Bravo",
                    "detected_attributes": [],
                    "confidence": {"score": 0.76, "label": "medium"},
                    "barcode": "3210987654321",
                },
                citations=[
                    {
                        "source": "OpenFoodFacts",
                        "title": "Strawberry Yogurt",
                        "field": "nutriments",
                        "field_label": "Nutrition",
                        "value": "Energy 120.0kcal - Sugars 12.0g",
                        "url": "https://world.openfoodfacts.org/product/3210987654321",
                    },
                    {
                        "source": "OpenFoodFacts",
                        "title": "Strawberry Yogurt",
                        "field": "labels_tags",
                        "field_label": "Labels",
                        "value": "No artificial colors",
                        "url": "https://world.openfoodfacts.org/product/3210987654321",
                    },
                ],
                product_enrichment={
                    "nutrition_summary": {
                        "energy_kcal_100g": "120.0",
                        "sugars_100g": "12.0",
                        "fat_100g": "2.0",
                        "saturated_fat_100g": "1.0",
                        "proteins_100g": "7.0",
                        "salt_100g": "0.2",
                    },
                    "nutrition_grade": "C",
                    "labels": ["No artificial colors"],
                    "additives": ["E330"],
                    "enrichment_source_confidence": "high",
                    "enrichment_notes": [],
                },
            ),
        },
    }


def post_compare(payload):
    return TestClient(app).post("/v1/compare/products", json=payload)


def difference_by_field(body, field):
    return next(diff for diff in body["differences"] if diff["field"] == field)


def test_compare_requires_two_products():
    response = post_compare({"product_a": compare_payload()["product_a"]})

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "compare_missing_product"
    assert body["request_id"]


def test_compare_returns_differences_for_nutrition():
    product_a = analysis_context()
    product_b = analysis_context(
        request_id="analysis-request-b",
        product={
            "display_name": "Plain Yogurt B",
            "category": "yogurt",
            "brand": "Bravo",
            "detected_attributes": [],
            "confidence": {"score": 0.7, "label": "medium"},
            "barcode": None,
        },
    )
    product_a["product_enrichment"]["nutrition_summary"]["sugars_100g"] = "0.0"
    product_b["product_enrichment"]["nutrition_summary"]["sugars_100g"] = None

    response = post_compare(compare_payload(product_a, product_b))

    assert response.status_code == 200
    body = response.json()
    assert difference_by_field(body, "energy_kcal_100g")["status"] == "same"
    sugars = difference_by_field(body, "sugars_100g")
    assert sugars["product_a_value"] == "0.0"
    assert sugars["product_b_value"] is None
    assert sugars["status"] == "missing_b"


def test_compare_citations_are_subset():
    payload = compare_payload()
    response = post_compare(payload)

    assert response.status_code == 200
    body = response.json()
    original = {
        (citation["source"], citation["field"], citation["url"])
        for product in [payload["product_a"], payload["product_b"]]
        for citation in product["analysis"]["citations"]
    }
    used = {
        (citation["source"], citation["field"], citation["url"])
        for citation in body["citations_used"]
    }
    assert used
    assert used.issubset(original)


def test_compare_handles_missing_fields():
    product_a = analysis_context()
    product_b = analysis_context(
        request_id="analysis-request-b",
        product={
            "display_name": "Unknown snack",
            "category": "snack",
            "brand": None,
            "detected_attributes": [],
            "confidence": {"score": 0.4, "label": "low"},
            "barcode": None,
        },
        product_enrichment=None,
        citations=[],
        grounding_status="no_match",
        grounding_summary="No reliable OpenFoodFacts match found",
        match_method="none",
    )

    response = post_compare(compare_payload(product_a, product_b))

    assert response.status_code == 200
    body = response.json()
    assert difference_by_field(body, "energy_kcal_100g")["status"] == "missing_b"
    assert difference_by_field(body, "nutrition_grade")["status"] == "missing_b"


def test_compare_does_not_require_images():
    payload = compare_payload()
    serialized = str(payload).lower()
    assert "image_bytes" not in serialized
    assert "base64" not in serialized
    assert "audio" not in serialized

    response = post_compare(payload)

    assert response.status_code == 200
    assert response.json()["summary"]


def test_compare_rejects_insufficient_comparable_data():
    minimal = analysis_context(
        request_id="empty-analysis",
        product={
            "display_name": "",
            "category": "",
            "brand": None,
            "detected_attributes": [],
            "confidence": {"score": 0.0, "label": "low"},
            "barcode": None,
        },
        citations=[],
        product_enrichment=None,
        grounding_status="no_match",
        grounding_summary="",
        match_method="none",
    )
    payload = compare_payload(copy.deepcopy(minimal), copy.deepcopy(minimal))

    response = post_compare(payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "compare_insufficient_data"
    assert body["message"] == "Neither product has enough data to compare."
