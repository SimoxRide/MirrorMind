"""Entity and relationship extraction pipeline for GraphRAG.

This module extracts structured entities/relationships from text
(persona data, interview answers, memories, writing samples)
and upserts them into Neo4j.
"""

from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.graphrag.neo4j_client import get_neo4j_client

logger = get_logger("graph_ingestion")


class GraphIngestionPipeline:
    """Explicit, debuggable ingestion pipeline for GraphRAG."""

    def __init__(self) -> None:
        self.client = get_neo4j_client()

    async def ingest_entity(
        self,
        persona_id: UUID,
        uid: str,
        name: str,
        entity_type: str,
        source: str,
        confidence: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upsert a single entity node."""
        props = properties or {}
        query = """
        MERGE (n:Entity {uid: $uid})
        ON CREATE SET n.created_at = datetime()
        SET n.name = $name,
            n.type = $entity_type,
            n.persona_id = $persona_id,
            n.source = $source,
            n.confidence = $confidence,
            n.updated_at = datetime()
        SET n += $properties
        RETURN n {.uid, .name, .type, .confidence} AS node
        """
        records = await self.client.run_query(
            query,
            {
                "uid": uid,
                "name": name,
                "entity_type": entity_type,
                "persona_id": str(persona_id),
                "source": source,
                "confidence": confidence,
                "properties": props,
            },
        )
        logger.info("entity_upserted", uid=uid, type=entity_type)
        return records[0]["node"] if records else {}

    async def ingest_relationship(
        self,
        source_uid: str,
        target_uid: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upsert a relationship between two entities."""
        props = properties or {}
        query = f"""
        MATCH (a:Entity {{uid: $source_uid}})
        MATCH (b:Entity {{uid: $target_uid}})
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r.created_at = datetime()
        SET r += $properties,
            r.updated_at = datetime()
        RETURN type(r) AS rel_type, a.uid AS source, b.uid AS target
        """
        records = await self.client.run_query(
            query,
            {
                "source_uid": source_uid,
                "target_uid": target_uid,
                "properties": props,
            },
        )
        logger.info(
            "relationship_upserted", source=source_uid, target=target_uid, type=rel_type
        )
        return records[0] if records else {}

    async def ingest_from_memory(
        self, persona_id: UUID, memory: dict[str, Any]
    ) -> None:
        """Extract entities from a memory record and ingest them.

        Uses a simple heuristic approach for MVP.
        For production, plug in an LLM-based extraction step.
        """
        # Create the memory itself as a node
        memory_uid = f"memory:{memory['id']}"
        await self.ingest_entity(
            persona_id=persona_id,
            uid=memory_uid,
            name=memory.get("title", "Untitled Memory"),
            entity_type=memory.get("memory_type", "memory"),
            source="memory_ingestion",
            confidence=memory.get("confidence", 1.0),
            properties={
                "content_preview": (memory.get("content", ""))[:500],
                "tags": memory.get("tags", []),
            },
        )

        # Link to any referenced entities
        for entity_name in memory.get("linked_entities", []):
            entity_uid = f"entity:{entity_name.lower().replace(' ', '_')}"
            await self.ingest_entity(
                persona_id=persona_id,
                uid=entity_uid,
                name=entity_name,
                entity_type="Topic",
                source="memory_extraction",
                confidence=0.8,
            )
            await self.ingest_relationship(
                source_uid=memory_uid,
                target_uid=entity_uid,
                rel_type="LINKED_TO",
                properties={"source": "auto_extraction"},
            )

    async def extract_entities_llm(
        self, persona_id: UUID, text: str, source: str
    ) -> list[dict[str, Any]]:
        """Extract entities using OpenAI.

        TODO: Requires OPENAI_API_KEY to be set.
        Returns list of extracted entities for review before ingestion.
        """
        settings = get_settings()
        if not settings.openai_api_key:
            logger.warning("openai_not_configured_skipping_llm_extraction")
            return []

        import openai

        client_kwargs: dict = {"api_key": settings.openai_api_key}
        if settings.openai_api_base:
            client_kwargs["base_url"] = settings.openai_api_base
        client = openai.AsyncOpenAI(**client_kwargs)
        prompt = f"""Extract entities and relationships from the following text.
Return a JSON object with:
- "entities": list of {{"uid": "<unique_id>", "name": "<name>", "type": "<Person|Place|Event|Value|Habit|Topic|Project|Decision>", "confidence": 0.0-1.0}}
- "relationships": list of {{"source": "<uid>", "target": "<uid>", "type": "<KNOWS|WORKS_WITH|RELATES_TO|VALUES|TRIGGERS|LINKED_TO>", "label": "<description>"}}

Text:
{text[:3000]}
"""
        response = await client.responses.create(
            model=settings.openai_model,
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        import json

        try:
            extracted = json.loads(response.output_text)
            return extracted.get("entities", [])
        except (json.JSONDecodeError, AttributeError):
            logger.warning("llm_extraction_parse_failed")
            return []
