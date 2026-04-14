"""Graph API routes — query, ingest, subgraph fetch, CRUD."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.graphrag.ingestion import GraphIngestionPipeline
from app.graphrag.retrieval import GraphRetriever
from app.schemas.core import (
    GraphEdge,
    GraphEdgeCreate,
    GraphEdgeUpdate,
    GraphNode,
    GraphNodeUpdate,
    GraphQueryRequest,
    GraphSubgraph,
)

logger = get_logger("graph")

router = APIRouter(prefix="/graph", tags=["GraphRAG"])


@router.post("/query", response_model=GraphSubgraph)
async def query_graph(req: GraphQueryRequest):
    """Fetch a subgraph for visualization or inspection."""
    retriever = GraphRetriever()
    result = await retriever.get_subgraph(
        persona_id=req.persona_id,
        node_type=req.node_type,
        query_text=req.query,
        depth=req.depth,
        limit=req.limit,
    )
    return GraphSubgraph(
        nodes=[
            {
                "id": n["id"],
                "label": n["label"],
                "type": n["type"],
                "properties": n.get("properties", {}),
            }
            for n in result["nodes"]
        ],
        edges=[
            {
                "id": e["id"],
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
                "properties": e.get("properties", {}),
            }
            for e in result["edges"]
        ],
    )


@router.post("/ingest/memory")
async def ingest_memory_to_graph(
    persona_id: UUID = Query(...),
    memory_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a single memory record into the knowledge graph."""
    from app.services.memory_service import MemoryService

    svc = MemoryService(db)
    memory = await svc.get(memory_id)
    if not memory:
        return {"status": "error", "detail": "Memory not found"}

    pipeline = GraphIngestionPipeline()
    await pipeline.ingest_from_memory(
        persona_id=persona_id,
        memory={
            "id": str(memory.id),
            "title": memory.title,
            "content": memory.content,
            "memory_type": memory.memory_type,
            "confidence": memory.confidence,
            "tags": memory.tags or [],
            "linked_entities": memory.linked_entities or [],
        },
    )
    return {"status": "ok", "memory_id": str(memory_id)}


@router.post("/rebuild")
async def rebuild_graph(
    persona_id: UUID = Query(...), db: AsyncSession = Depends(get_db)
):
    """Rebuild the full graph for a persona from all memories, streaming progress via SSE."""
    from app.services.memory_service import MemoryService

    svc = MemoryService(db)
    memories = await svc.list_by_persona(persona_id, limit=1000)
    total = len(memories)

    if total == 0:
        return {"status": "ok", "memories_processed": 0}

    async def event_stream():
        pipeline = GraphIngestionPipeline()
        count = 0
        for mem in memories:
            await pipeline.ingest_from_memory(
                persona_id=persona_id,
                memory={
                    "id": str(mem.id),
                    "title": mem.title,
                    "content": mem.content,
                    "memory_type": mem.memory_type,
                    "confidence": mem.confidence,
                    "tags": mem.tags or [],
                    "linked_entities": mem.linked_entities or [],
                },
            )
            count += 1
            progress = {
                "current": count,
                "total": total,
                "percent": round(count / total * 100),
                "current_memory": mem.title,
                "status": "processing",
            }
            yield f"data: {json.dumps(progress)}\n\n"
            logger.info(
                "graph_rebuild_progress", current=count, total=total, memory=mem.title
            )

        done = {
            "current": total,
            "total": total,
            "percent": 100,
            "status": "done",
            "current_memory": "",
        }
        yield f"data: {json.dumps(done)}\n\n"
        logger.info("graph_rebuild_complete", memories_processed=total)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Node CRUD ────────────────────────────────────────────


@router.patch("/nodes/{node_id}", response_model=GraphNode)
async def update_node(node_id: str, body: GraphNodeUpdate):
    """Update a node's label, type, or properties."""
    retriever = GraphRetriever()
    result = await retriever.update_node(
        node_id,
        label=body.label,
        node_type=body.type,
        properties=body.properties,
    )
    if not result:
        raise HTTPException(404, "Node not found or no changes applied")
    props = result.get("properties") or {}
    return GraphNode(
        id=result["id"],
        label=result["label"],
        type=result["type"],
        properties={k: v for k, v in props.items() if k not in ("uid", "persona_id")},
    )


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str):
    """Delete a node and all its relationships."""
    retriever = GraphRetriever()
    ok = await retriever.delete_node(node_id)
    if not ok:
        raise HTTPException(404, "Node not found")
    return {"status": "ok"}


# ── Edge CRUD ────────────────────────────────────────────


@router.post("/edges", response_model=GraphEdge)
async def create_edge(body: GraphEdgeCreate):
    """Create a new relationship between two nodes."""
    retriever = GraphRetriever()
    result = await retriever.create_edge(
        body.source, body.target, body.type, body.properties or None
    )
    if not result:
        raise HTTPException(404, "Source or target node not found")
    return GraphEdge(**result)


@router.patch("/edges/{edge_id:path}", response_model=GraphEdge)
async def update_edge(edge_id: str, body: GraphEdgeUpdate):
    """Update an edge's type or properties."""
    retriever = GraphRetriever()
    result = await retriever.update_edge(
        edge_id, edge_type=body.type, properties=body.properties
    )
    if not result:
        raise HTTPException(404, "Edge not found or no changes applied")
    return GraphEdge(**result)


@router.delete("/edges/{edge_id:path}")
async def delete_edge(edge_id: str):
    """Delete a relationship."""
    retriever = GraphRetriever()
    ok = await retriever.delete_edge(edge_id)
    if not ok:
        raise HTTPException(404, "Edge not found")
    return {"status": "ok"}
