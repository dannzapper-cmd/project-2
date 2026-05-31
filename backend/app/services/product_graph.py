import time

from app.config import Settings, is_neo4j_configured
from app.schemas import AnalyzeImageResponse, ProductGraphResponse
from app.services.graph_builder import (
    build_graph_from_analysis,
    format_evidence_paths_for_chat,
    graph_contains_forbidden_payload,
)
from app.services.neo4j_graph import Neo4jGraphError, sync_graph_to_neo4j


def _latency_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def build_product_graph_response(
    *,
    analysis: AnalyzeImageResponse,
    request_id: str,
    settings: Settings,
    started_at: float,
) -> ProductGraphResponse:
    built = build_graph_from_analysis(analysis)
    payload = {
        "nodes": [node.model_dump() for node in built.nodes],
        "edges": [edge.model_dump() for edge in built.edges],
    }
    if graph_contains_forbidden_payload(payload):
        raise ValueError("Graph payload contains disallowed media or identifiers")

    graph_backend: str = "memory"
    if settings.graph_enabled and is_neo4j_configured(settings):
        try:
            sync_graph_to_neo4j(
                settings=settings,
                nodes=built.nodes,
                edges=built.edges,
                source_product_id=analysis.source_product_id,
            )
            graph_backend = "neo4j"
        except (Neo4jGraphError, Exception):  # noqa: BLE001
            graph_backend = "neo4j_fallback"

    return ProductGraphResponse(
        nodes=built.nodes,
        edges=built.edges,
        evidence_paths=built.evidence_paths,
        graph_backend=graph_backend,  # type: ignore[arg-type]
        graph_enabled=settings.graph_enabled,
        request_id=request_id,
        latency_ms=_latency_ms(started_at),
    )


def graph_context_for_chat(analysis: AnalyzeImageResponse) -> str:
    built = build_graph_from_analysis(analysis)
    return format_evidence_paths_for_chat(built.evidence_paths)
