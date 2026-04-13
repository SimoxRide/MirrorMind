"""Health / admin routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_optional_current_user
from app.db.session import get_db
from app.graphrag.neo4j_client import get_neo4j_client
from app.models.user import User
from app.services.provider_settings import resolve_provider_settings

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
async def health_openai(user: User | None = Depends(get_optional_current_user)):
    resolved = resolve_provider_settings(user)
    return {
        "openai_configured": resolved.configured,
        "model": resolved.model,
        "api_base": resolved.effective_api_base,
        "api_key_source": resolved.source,
        "has_user_api_key": resolved.has_user_api_key,
        "has_env_api_key": resolved.has_env_api_key,
    }
