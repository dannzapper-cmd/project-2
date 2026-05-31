import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.config import Settings, is_neo4j_configured
from app.main import app
from app.schemas import (
    AnalyzeImageResponse,
    Citation,
    Confidence,
    Insight,
    NutritionSummary,
    PrivacySummary,
    ProductEnrichment,
    ProductSummary,
    ResponseMeta,
)
from app.services.graph_builder import (
    build_graph_from_analysis,
    graph_contains_forbidden_payload,
)
from app.services.product_graph import build_product_graph_response


def mock_analysis(**overrides) -> AnalyzeImageResponse:
    base = AnalyzeImageResponse(
        request_id="graph-test-request",
        mode="mock_fallback",
        status="completed",
        product=ProductSummary(
            display_name="Organic Greek Yogurt Plain",
            category="Dairies, Yogurts",
            brand="Acme",
            detected_attributes=["packaged food"],
            confidence=Confidence(score=0.72, label="medium"),
            barcode="1234567890123",
        ),
        insights=[
            Insight(
                title="Label match",
                body="Packaging resembles a plain yogurt tub.",
                type="visual",
            )
        ],
        warnings=["High sugar per 100g may be relevant if you limit added sugars."],
        citations=[
            Citation(
                title="Organic Greek Yogurt Plain",
                field="product_name",
                field_label="Product Name",
                value="Organic Greek Yogurt Plain",
                url="https://world.openfoodfacts.org/product/1234567890123",
            ),
            Citation(
                title="Organic Greek Yogurt Plain",
                field="categories",
                field_label="Categories",
                value="Dairies, Fermented foods, Yogurts",
                url="https://world.openfoodfacts.org/product/1234567890123",
            ),
            Citation(
                title="Organic Greek Yogurt Plain",
                field="nutriments",
                field_label="Nutrition",
                value="Energy 234.0kcal - Sugars 12.3g - Fat 8.1g",
                url="https://world.openfoodfacts.org/product/1234567890123",
            ),
            Citation(
                title="Organic Greek Yogurt Plain",
                field="additives_tags",
                field_label="Additives",
                value="E102 - E330",
                url="https://world.openfoodfacts.org/product/1234567890123",
            ),
            Citation(
                title="Organic Greek Yogurt Plain",
                field="ingredients_text",
                field_label="Ingredients",
                value="Milk, live cultures.",
                url="https://world.openfoodfacts.org/product/1234567890123",
            ),
        ],
        next_questions=[],
        privacy=PrivacySummary(image_stored=False, image_retention="none"),
        meta=ResponseMeta(model="mock", latency_ms=120, api_version="v1"),
        grounding_status="grounded",
        grounding_summary="Matched by barcode",
        match_method="barcode",
        source_product_id="1234567890123",
        product_enrichment=ProductEnrichment(
            nutrition_summary=NutritionSummary(
                energy_kcal_100g="234.0",
                sugars_100g="12.3",
                fat_100g="8.1",
                saturated_fat_100g="4.2",
                proteins_100g="9.0",
                salt_100g="0.2",
            ),
            nutrition_grade="A",
            labels=["Organic"],
            additives=["E102", "E330"],
            enrichment_source_confidence="high",
            enrichment_notes=["Nutrition values are per 100g when available."],
        ),
    )
    payload = base.model_dump()
    payload.update(overrides)
    return AnalyzeImageResponse.model_validate(payload)


def test_graph_builder_returns_expected_nodes_and_edges():
    analysis = mock_analysis()
    built = build_graph_from_analysis(analysis)

    node_types = {node.type for node in built.nodes}
    assert "product" in node_types
    assert "brand" in node_types
    assert "category" in node_types
    assert "nutrition" in node_types
    assert "additive" in node_types
    assert "warning" in node_types
    assert "citation" in node_types
    assert "alternative" in node_types
    assert len(built.edges) > 0
    assert any(path.path_type == "warning_nutrition_citation" for path in built.evidence_paths)
    assert any(path.path_type == "additive_warning_citation" for path in built.evidence_paths)


def test_fallback_mode_returns_non_empty_graph():
    settings = Settings(
        gemini_api_key=None,
        gemini_model="gemini-2.5-flash",
        analysis_mode="mock",
        mock_fallback_allowed=False,
        cache_enabled=True,
        cache_ttl_seconds=900,
        cache_max_entries=50,
        max_image_mb=8,
        graph_enabled=True,
        neo4j_uri=None,
        neo4j_username=None,
        neo4j_password=None,
    )
    response = build_product_graph_response(
        analysis=mock_analysis(),
        request_id="graph-req",
        settings=settings,
        started_at=0.0,
    )
    assert len(response.nodes) > 0
    assert len(response.edges) > 0
    assert response.graph_backend == "memory"


def test_neo4j_disabled_uses_memory_without_exception(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    client = TestClient(app)
    response = client.post(
        "/v1/graph/product",
        json={"analysis": mock_analysis().model_dump(mode="json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["graph_backend"] == "memory"
    assert len(body["nodes"]) > 0


def test_graph_payload_rejects_media_and_secrets():
    analysis = mock_analysis()
    built = build_graph_from_analysis(analysis)
    payload = {
        "nodes": [node.model_dump() for node in built.nodes],
        "edges": [edge.model_dump() for edge in built.edges],
    }
    assert graph_contains_forbidden_payload(payload) is False

    unsafe = copy.deepcopy(payload)
    unsafe["nodes"][0]["detail"] = "data:image/png;base64,abc"
    assert graph_contains_forbidden_payload(unsafe) is True

    unsafe_secret = copy.deepcopy(payload)
    unsafe_secret["request_id"] = "secret-session"
    assert graph_contains_forbidden_payload(unsafe_secret) is True


def test_is_neo4j_configured_requires_all_env_vars():
    partial = Settings(
        gemini_api_key=None,
        gemini_model="gemini-2.5-flash",
        analysis_mode="mock",
        mock_fallback_allowed=False,
        cache_enabled=True,
        cache_ttl_seconds=900,
        cache_max_entries=50,
        max_image_mb=8,
        graph_enabled=True,
        neo4j_uri="neo4j+s://example.databases.neo4j.io",
        neo4j_username=None,
        neo4j_password=None,
    )
    assert is_neo4j_configured(partial) is False
