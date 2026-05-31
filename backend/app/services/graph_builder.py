import hashlib
import re
from typing import Iterable

from app.schemas import (
    AnalyzeImageResponse,
    Citation,
    EvidencePath,
    EvidencePathStep,
    GraphEdge,
    GraphNode,
    GraphNodeType,
)


FORBIDDEN_GRAPH_KEYS = {
    "image",
    "image_bytes",
    "image_base64",
    "base64",
    "audio",
    "audio_bytes",
    "audio_base64",
    "request_id",
    "session",
    "session_id",
    "user_id",
    "email",
    "phone",
    "password",
    "secret",
    "api_key",
    "gemini_api_key",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"data:image/", re.IGNORECASE),
    re.compile(r"data:audio/", re.IGNORECASE),
    re.compile(r"^[A-Za-z0-9+/]{200,}={0,2}$"),
]


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "node"


def _node_id(node_type: GraphNodeType, key: str) -> str:
    digest = hashlib.sha256(f"{node_type}:{key}".encode()).hexdigest()[:12]
    return f"{node_type}-{digest}"


def _truncate(value: str, max_length: int = 280) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _citation_by_field(
    citations: Iterable[Citation], field: str
) -> Citation | None:
    for citation in citations:
        if citation.field == field:
            return citation
    return None


def graph_contains_forbidden_payload(graph: dict) -> bool:
    """Return True when graph payload may contain media, PII, or secrets."""

    def walk(value: object, parent_key: str | None = None) -> bool:
        if isinstance(value, dict):
            for key, nested in value.items():
                lowered = str(key).lower()
                if lowered in FORBIDDEN_GRAPH_KEYS:
                    return True
                if walk(nested, lowered):
                    return True
            return False
        if isinstance(value, list):
            return any(walk(item, parent_key) for item in value)
        if isinstance(value, str):
            if parent_key in FORBIDDEN_GRAPH_KEYS:
                return True
            return any(pattern.search(value) for pattern in FORBIDDEN_VALUE_PATTERNS)
        return False

    return walk(graph)


def graph_validation_payload(
    *,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    evidence_paths: list[EvidencePath],
) -> dict:
    """Serialize graph structures for privacy scanning before return/sync."""
    return {
        "nodes": [node.model_dump() for node in nodes],
        "edges": [edge.model_dump() for edge in edges],
        "evidence_paths": [path.model_dump() for path in evidence_paths],
    }


class GraphBuildResult:
    def __init__(
        self,
        *,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        evidence_paths: list[EvidencePath],
    ) -> None:
        self.nodes = nodes
        self.edges = edges
        self.evidence_paths = evidence_paths


def build_graph_from_analysis(analysis: AnalyzeImageResponse) -> GraphBuildResult:
    """
    Build an in-memory product evidence graph from a completed analysis.
    Never includes image bytes, audio, prompts, secrets, or session identifiers.
    """
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    evidence_paths: list[EvidencePath] = []
    node_index: dict[str, GraphNode] = {}

    def add_node(
        node_type: GraphNodeType,
        key: str,
        *,
        label: str,
        detail: str | None = None,
        confidence: float | None = None,
        field: str | None = None,
        url: str | None = None,
    ) -> GraphNode:
        node_id = _node_id(node_type, key)
        if node_id in node_index:
            return node_index[node_id]
        node = GraphNode(
            id=node_id,
            type=node_type,
            label=_truncate(label, 120),
            detail=_truncate(detail) if detail else None,
            confidence=confidence,
            field=field,
            url=url,
        )
        node_index[node_id] = node
        nodes.append(node)
        return node

    def add_edge(source: GraphNode, target: GraphNode, relationship: str, label: str | None = None) -> None:
        edge_id = f"{source.id}->{target.id}:{relationship}"
        if any(edge.id == edge_id for edge in edges):
            return
        edges.append(
            GraphEdge(
                id=edge_id,
                source=source.id,
                target=target.id,
                relationship=relationship,
                label=label,
            )
        )

    product = analysis.product
    product_node = add_node(
        "product",
        product.display_name,
        label=product.display_name,
        detail=f"Category: {product.category}",
        confidence=product.confidence.score,
    )

    category_node = add_node(
        "category",
        product.category,
        label=product.category,
        detail="Product category from analysis",
    )
    add_edge(product_node, category_node, "in_category", "in category")

    if product.brand:
        brand_node = add_node(
            "brand",
            product.brand,
            label=product.brand,
            detail="Brand from visual analysis",
        )
        add_edge(product_node, brand_node, "has_brand", "brand")

    enrichment = analysis.product_enrichment
    nutrition_node: GraphNode | None = None
    if enrichment and enrichment.nutrition_summary:
        summary = enrichment.nutrition_summary
        parts = [
            f"Energy {summary.energy_kcal_100g} kcal/100g"
            if summary.energy_kcal_100g
            else None,
            f"Sugars {summary.sugars_100g} g/100g" if summary.sugars_100g else None,
            f"Fat {summary.fat_100g} g/100g" if summary.fat_100g else None,
            f"Protein {summary.proteins_100g} g/100g"
            if summary.proteins_100g
            else None,
            f"Salt {summary.salt_100g} g/100g" if summary.salt_100g else None,
        ]
        nutrition_detail = " · ".join(part for part in parts if part)
        nutrition_node = add_node(
            "nutrition",
            f"{product.display_name}-nutrition",
            label="Nutrition (per 100g)",
            detail=nutrition_detail or "OpenFoodFacts nutrition fields",
            field="nutriments",
        )
        add_edge(product_node, nutrition_node, "has_nutrition", "nutrition")
        if enrichment.nutrition_grade:
            add_node(
                "nutrition",
                f"{product.display_name}-grade",
                label=f"Nutri-Score {enrichment.nutrition_grade}",
                detail="Nutrition grade from OpenFoodFacts",
                field="nutrition_grades",
            )

    ingredients_citation = _citation_by_field(analysis.citations, "ingredients_text")
    if ingredients_citation:
        ingredient_node = add_node(
            "ingredient",
            ingredients_citation.value[:80],
            label="Ingredients",
            detail=ingredients_citation.value,
            field=ingredients_citation.field,
            url=ingredients_citation.url,
        )
        add_edge(product_node, ingredient_node, "contains", "ingredients")

    if enrichment and enrichment.additives:
        for additive in enrichment.additives[:8]:
            additive_node = add_node(
                "additive",
                additive,
                label=additive,
                detail="Additive listed in OpenFoodFacts enrichment",
                field="additives_tags",
            )
            add_edge(product_node, additive_node, "contains_additive", "additive")

    citation_nodes: dict[str, GraphNode] = {}
    for citation in analysis.citations:
        citation_node = add_node(
            "citation",
            f"{citation.field}:{citation.value[:60]}",
            label=citation.field_label,
            detail=citation.value,
            field=citation.field,
            url=citation.url,
        )
        citation_nodes[citation.field] = citation_node
        add_edge(product_node, citation_node, "cited_by", "source")

        if citation.field == "nutriments" and nutrition_node:
            add_edge(nutrition_node, citation_node, "grounded_in", "OpenFoodFacts")
        if citation.field == "ingredients_text" and "ingredient" in {
            node.type for node in nodes
        }:
            ingredient_match = next(
                (node for node in nodes if node.type == "ingredient"), None
            )
            if ingredient_match:
                add_edge(ingredient_match, citation_node, "grounded_in", "OpenFoodFacts")
        if citation.field == "additives_tags":
            for additive_node in [node for node in nodes if node.type == "additive"]:
                add_edge(additive_node, citation_node, "grounded_in", "OpenFoodFacts")

    warning_nodes: list[GraphNode] = []
    for index, warning in enumerate(analysis.warnings[:6]):
        warning_node = add_node(
            "warning",
            f"{index}:{warning[:80]}",
            label=_truncate(warning, 80),
            detail=warning,
        )
        warning_nodes.append(warning_node)
        add_edge(product_node, warning_node, "has_warning", "warning")

        citation_node = citation_nodes.get("nutriments")
        if nutrition_node and citation_node:
            add_edge(warning_node, nutrition_node, "relates_to", "nutrition field")
            if citation_node:
                add_edge(warning_node, citation_node, "supported_by", "citation")
                evidence_paths.append(
                    EvidencePath(
                        id=f"path-warning-{index}",
                        path_type="warning_nutrition_citation",
                        summary=(
                            f"{warning_node.label} → nutrition field → "
                            f"{citation_node.label} (OpenFoodFacts)"
                        ),
                        steps=[
                            EvidencePathStep(
                                node_id=warning_node.id,
                                node_type="warning",
                                label=warning_node.label,
                            ),
                            EvidencePathStep(
                                node_id=nutrition_node.id,
                                node_type="nutrition",
                                label=nutrition_node.label,
                            ),
                            EvidencePathStep(
                                node_id=citation_node.id,
                                node_type="citation",
                                label=citation_node.label,
                            ),
                        ],
                        citation_field="nutriments",
                    )
                )

    for additive_node in [node for node in nodes if node.type == "additive"]:
        additives_citation = citation_nodes.get("additives_tags")
        related_warning = warning_nodes[0] if warning_nodes else None
        if additives_citation:
            if related_warning:
                add_edge(
                    additive_node,
                    related_warning,
                    "contextual_warning",
                    "contextual warning",
                )
            add_edge(additive_node, additives_citation, "grounded_in", "citation")
            steps = [
                EvidencePathStep(
                    node_id=additive_node.id,
                    node_type="additive",
                    label=additive_node.label,
                )
            ]
            if related_warning:
                steps.append(
                    EvidencePathStep(
                        node_id=related_warning.id,
                        node_type="warning",
                        label=related_warning.label,
                    )
                )
            steps.append(
                EvidencePathStep(
                    node_id=additives_citation.id,
                    node_type="citation",
                    label=additives_citation.label,
                )
            )
            evidence_paths.append(
                EvidencePath(
                    id=f"path-additive-{_slug(additive_node.label)}",
                    path_type="additive_warning_citation",
                    summary=(
                        f"{additive_node.label} → "
                        + (
                            f"warning context ({related_warning.label}) → "
                            if related_warning
                            else ""
                        )
                        + f"{additives_citation.label} (OpenFoodFacts)"
                    ),
                    steps=steps,
                    citation_field="additives_tags",
                )
            )

    categories_citation = citation_nodes.get("categories") or _citation_by_field(
        analysis.citations, "categories"
    )
    if categories_citation:
        alt_node = add_node(
            "alternative",
            f"alt-{product.category}",
            label="Category alternatives",
            detail=(
                "Products in the same category may be compared using "
                "SnapInsight Compare Mode with a second scan."
            ),
            field="categories",
        )
        add_edge(alt_node, category_node, "matches_category", "category match")
        citation_node = citation_nodes.get("categories")
        if citation_node:
            add_edge(alt_node, citation_node, "comparison_evidence", "citation")
            evidence_paths.append(
                EvidencePath(
                    id="path-alternative-category",
                    path_type="alternative_category_citation",
                    summary=(
                        f"{alt_node.label} → {category_node.label} → "
                        f"{citation_node.label} (comparison evidence)"
                    ),
                    steps=[
                        EvidencePathStep(
                            node_id=alt_node.id,
                            node_type="alternative",
                            label=alt_node.label,
                        ),
                        EvidencePathStep(
                            node_id=category_node.id,
                            node_type="category",
                            label=category_node.label,
                        ),
                        EvidencePathStep(
                            node_id=citation_node.id,
                            node_type="citation",
                            label=citation_node.label,
                        ),
                    ],
                    citation_field="categories",
                )
            )

    product_name_citation_node = citation_nodes.get("product_name")

    for insight in analysis.insights[:3]:
        if not product_name_citation_node:
            break
        citation_node = product_name_citation_node
        evidence_paths.append(
            EvidencePath(
                id=f"path-insight-{_slug(insight.title)}",
                path_type="insight_citation",
                summary=f"{insight.title} → {citation_node.label}",
                steps=[
                    EvidencePathStep(
                        node_id=product_node.id,
                        node_type="product",
                        label=insight.title,
                    ),
                    EvidencePathStep(
                        node_id=citation_node.id,
                        node_type="citation",
                        label=citation_node.label,
                    ),
                ],
                citation_field=citation_node.field,
            )
        )

    return GraphBuildResult(
        nodes=nodes,
        edges=edges,
        evidence_paths=evidence_paths,
    )


def format_evidence_paths_for_chat(
    evidence_paths: list[EvidencePath], *, max_paths: int = 3
) -> str:
    if not evidence_paths:
        return ""
    lines: list[str] = []
    for path in evidence_paths[:max_paths]:
        lines.append(path.summary)
    return "Graph evidence paths: " + " | ".join(lines)
