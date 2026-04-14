"""Graph retrieval — fetch subgraphs for clone generation and visualization."""

from typing import Any
from uuid import UUID

from neo4j.time import DateTime as Neo4jDateTime

from app.core.logging import get_logger
from app.graphrag.neo4j_client import get_neo4j_client

logger = get_logger("graph_retrieval")


class GraphRetriever:
    """Retrieve subgraphs from Neo4j for the clone pipeline and UI viewer."""

    def __init__(self) -> None:
        self.client = get_neo4j_client()

    async def get_subgraph(
        self,
        persona_id: UUID,
        *,
        node_type: str | None = None,
        query_text: str | None = None,
        depth: int = 2,
        limit: int = 100,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return nodes and edges for visualization.

        Filters by persona_id. Optionally filter by node type or search by name.
        """
        where_clauses = ["n.persona_id = $persona_id"]
        params: dict[str, Any] = {"persona_id": str(persona_id), "limit": limit}

        if node_type:
            where_clauses.append("n.type = $node_type")
            params["node_type"] = node_type

        if query_text:
            where_clauses.append("toLower(n.name) CONTAINS toLower($query_text)")
            params["query_text"] = query_text

        where = " AND ".join(where_clauses)

        # Fetch nodes matching filter
        node_query = f"""
        MATCH (n:Entity)
        WHERE {where}
        RETURN n.uid AS id, n.name AS label, n.type AS type,
               properties(n) AS properties
        LIMIT $limit
        """
        nodes_raw = await self.client.run_query(node_query, params)

        # Collect node UIDs for edge query
        node_ids = [n["id"] for n in nodes_raw]
        if not node_ids:
            return {"nodes": [], "edges": []}

        # Fetch edges between matched nodes (up to depth)
        edge_query = """
        MATCH (a:Entity)-[r]->(b:Entity)
        WHERE a.uid IN $node_ids AND b.uid IN $node_ids
        RETURN a.uid AS source, b.uid AS target, type(r) AS type,
               elementId(r) AS edge_id, properties(r) AS properties
        """
        edges_raw = await self.client.run_query(edge_query, {"node_ids": node_ids})

        def _serialize_value(v: Any) -> Any:
            if isinstance(v, Neo4jDateTime):
                return v.isoformat()
            return v

        nodes = [
            {
                "id": n["id"],
                "label": n["label"],
                "type": n["type"],
                "properties": {
                    k: _serialize_value(v)
                    for k, v in (n.get("properties") or {}).items()
                    if k not in ("uid", "persona_id")
                },
            }
            for n in nodes_raw
        ]

        edges = [
            {
                "id": str(e["edge_id"]),
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
                "properties": {
                    k: _serialize_value(v)
                    for k, v in (e.get("properties") or {}).items()
                },
            }
            for e in edges_raw
        ]

        return {"nodes": nodes, "edges": edges}

    # ── CRUD operations ──────────────────────────────────

    async def update_node(
        self,
        node_id: str,
        *,
        label: str | None = None,
        node_type: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        sets: list[str] = []
        params: dict[str, Any] = {"uid": node_id}
        if label is not None:
            sets.append("n.name = $name")
            params["name"] = label
        if node_type is not None:
            sets.append("n.type = $type")
            params["type"] = node_type
        if properties is not None:
            for k, v in properties.items():
                if k in ("uid", "persona_id"):
                    continue
                safe_key = k.replace(" ", "_")
                sets.append(f"n.`{safe_key}` = $prop_{safe_key}")
                params[f"prop_{safe_key}"] = v
        if not sets:
            return None
        query = f"""
        MATCH (n:Entity {{uid: $uid}})
        SET {', '.join(sets)}
        RETURN n.uid AS id, n.name AS label, n.type AS type, properties(n) AS properties
        """
        rows = await self.client.run_query(query, params)
        return rows[0] if rows else None

    async def delete_node(self, node_id: str) -> bool:
        query = """
        MATCH (n:Entity {uid: $uid})
        DETACH DELETE n
        RETURN count(*) AS deleted
        """
        rows = await self.client.run_query(query, {"uid": node_id})
        return bool(rows and rows[0].get("deleted", 0) > 0)

    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        props_str = ""
        params: dict[str, Any] = {"src": source_id, "tgt": target_id}
        if properties:
            prop_parts = []
            for k, v in properties.items():
                safe_key = k.replace(" ", "_")
                prop_parts.append(f"`{safe_key}`: $prop_{safe_key}")
                params[f"prop_{safe_key}"] = v
            props_str = " {" + ", ".join(prop_parts) + "}"

        safe_type = edge_type.replace(" ", "_").upper()
        query = f"""
        MATCH (a:Entity {{uid: $src}}), (b:Entity {{uid: $tgt}})
        CREATE (a)-[r:`{safe_type}`{props_str}]->(b)
        RETURN a.uid AS source, b.uid AS target, type(r) AS type,
               elementId(r) AS edge_id, properties(r) AS properties
        """
        rows = await self.client.run_query(query, params)
        if not rows:
            return None
        e = rows[0]
        return {
            "id": str(e["edge_id"]),
            "source": e["source"],
            "target": e["target"],
            "type": e["type"],
            "properties": e.get("properties") or {},
        }

    async def update_edge(
        self,
        edge_id: str,
        *,
        edge_type: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if edge_type is not None:
            # Neo4j doesn't allow changing relationship type directly;
            # we must delete and recreate with new type.
            fetch = """
            MATCH (a)-[r]->(b) WHERE elementId(r) = $eid
            RETURN a.uid AS src, b.uid AS tgt, type(r) AS old_type, properties(r) AS props
            """
            rows = await self.client.run_query(fetch, {"eid": edge_id})
            if not rows:
                return None
            old = rows[0]
            merged_props = old.get("props") or {}
            if properties:
                merged_props.update(properties)
            # Remove internal Neo4j props that shouldn't be set back
            for key in list(merged_props):
                if key.startswith("_"):
                    del merged_props[key]
            # Delete old
            await self.client.run_query(
                "MATCH ()-[r]->() WHERE elementId(r) = $eid DELETE r", {"eid": edge_id}
            )
            return await self.create_edge(
                old["src"], old["tgt"], edge_type, merged_props or None
            )
        elif properties is not None:
            sets = []
            params: dict[str, Any] = {"eid": edge_id}
            for k, v in properties.items():
                safe_key = k.replace(" ", "_")
                sets.append(f"r.`{safe_key}` = $prop_{safe_key}")
                params[f"prop_{safe_key}"] = v
            if not sets:
                return None
            query = f"""
            MATCH (a)-[r]->(b) WHERE elementId(r) = $eid
            SET {', '.join(sets)}
            RETURN a.uid AS source, b.uid AS target, type(r) AS type,
                   elementId(r) AS edge_id, properties(r) AS properties
            """
            rows = await self.client.run_query(query, params)
            if not rows:
                return None
            e = rows[0]
            return {
                "id": str(e["edge_id"]),
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
                "properties": e.get("properties") or {},
            }
        return None

    async def delete_edge(self, edge_id: str) -> bool:
        query = """
        MATCH ()-[r]->() WHERE elementId(r) = $eid
        DELETE r
        RETURN count(*) AS deleted
        """
        rows = await self.client.run_query(query, {"eid": edge_id})
        return bool(rows and rows[0].get("deleted", 0) > 0)

    async def retrieve_for_context(
        self,
        persona_id: UUID,
        context_keywords: list[str],
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant graph nodes for the clone pipeline.

        Searches by keyword match on node names and connected neighbors.
        """
        if not context_keywords:
            return []

        query = """
        UNWIND $keywords AS keyword
        MATCH (n:Entity)
        WHERE n.persona_id = $persona_id
          AND toLower(n.name) CONTAINS toLower(keyword)
        OPTIONAL MATCH (n)-[r]-(neighbor:Entity)
        RETURN DISTINCT n.uid AS id, n.name AS name, n.type AS type,
               n.confidence AS confidence,
               collect(DISTINCT {name: neighbor.name, type: neighbor.type, rel: type(r)}) AS neighbors
        LIMIT $limit
        """
        records = await self.client.run_query(
            query,
            {
                "persona_id": str(persona_id),
                "keywords": context_keywords,
                "limit": limit,
            },
        )
        return records
