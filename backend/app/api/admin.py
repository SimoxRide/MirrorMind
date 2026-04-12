"""Health / admin routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.graphrag.neo4j_client import get_neo4j_client

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health")
async def health():
    return {"status": "ok", "version": get_settings().app_version}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"postgres": "connected"}
    except Exception as e:
        return {"postgres": "error", "detail": str(e)}


@router.get("/health/neo4j")
async def health_neo4j():
    try:
        client = get_neo4j_client()
        ok = await client.verify_connectivity()
        return {"neo4j": "connected" if ok else "error"}
    except Exception as e:
        return {"neo4j": "error", "detail": str(e)}


@router.get("/health/openai")
async def health_openai():
    settings = get_settings()
    configured = bool(settings.openai_api_key)
    return {
        "openai_configured": configured,
        "model": settings.openai_model,
        "api_base": settings.openai_api_base or "https://api.openai.com/v1 (default)",
    }
