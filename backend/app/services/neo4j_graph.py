import logging

from app.config import Settings
from app.schemas import GraphEdge, GraphNode


logger = logging.getLogger(__name__)


class Neo4jGraphError(Exception):
    pass


def _product_key(nodes: list[GraphNode]) -> str | None:
    for node in nodes:
        if node.type == "product":
            return node.id
    return None


def sync_graph_to_neo4j(
    *,
    settings: Settings,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    source_product_id: str | None,
) -> None:
    """
    Optionally persist public product graph nodes to Neo4j.
    Never stores request IDs, session identifiers, images, audio, or secrets.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise Neo4jGraphError("neo4j driver not installed") from exc

    if not settings.neo4j_uri or not settings.neo4j_username or not settings.neo4j_password:
        raise Neo4jGraphError("Neo4j credentials are not configured")

    product_key = source_product_id or _product_key(nodes)
    if not product_key:
        raise Neo4jGraphError("Missing product key for Neo4j sync")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    try:
        with driver.session() as session:
            session.execute_write(
                _write_graph_tx,
                product_key=product_key,
                nodes=[
                    {
                        "id": node.id,
                        "type": node.type,
                        "label": node.label,
                        "detail": node.detail,
                        "field": node.field,
                        "url": node.url,
                        "confidence": node.confidence,
                    }
                    for node in nodes
                ],
                edges=[
                    {
                        "id": edge.id,
                        "source": edge.source,
                        "target": edge.target,
                        "relationship": edge.relationship,
                        "label": edge.label,
                    }
                    for edge in edges
                ],
            )
    finally:
        driver.close()


def _write_graph_tx(tx, *, product_key: str, nodes: list[dict], edges: list[dict]) -> None:
    tx.run(
        """
        MERGE (p:SnapProduct {product_key: $product_key})
        SET p.updated_at = datetime()
        """,
        product_key=product_key,
    )
    for node in nodes:
        tx.run(
            """
            MATCH (p:SnapProduct {product_key: $product_key})
            MERGE (n:SnapGraphNode {node_id: $node_id})
            SET n.node_type = $node_type,
                n.label = $label,
                n.detail = $detail,
                n.field = $field,
                n.url = $url,
                n.confidence = $confidence
            MERGE (p)-[:HAS_NODE]->(n)
            """,
            product_key=product_key,
            node_id=node["id"],
            node_type=node["type"],
            label=node["label"],
            detail=node["detail"],
            field=node["field"],
            url=node["url"],
            confidence=node["confidence"],
        )
    for edge in edges:
        tx.run(
            """
            MATCH (source:SnapGraphNode {node_id: $source_id})
            MATCH (target:SnapGraphNode {node_id: $target_id})
            MERGE (source)-[r:SNAP_REL {rel_id: $rel_id}]->(target)
            SET r.relationship = $relationship,
                r.label = $label
            """,
            source_id=edge["source"],
            target_id=edge["target"],
            rel_id=edge["id"],
            relationship=edge["relationship"],
            label=edge["label"],
        )
