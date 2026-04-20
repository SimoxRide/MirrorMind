"""Health / admin routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_optional_current_user
from app.db.session import get_db
from app.graphrag.neo4j_client import get_neo4j_client
from app.models.user import User
from app.services.provider_settings import resolve_provider_settings

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health", summary="Liveness probe")
async def health():
    """Basic liveness check — returns OK if the process is running."""
    return {"status": "ok", "version": get_settings().app_version}


@router.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Readiness probe — all critical dependencies must be reachable."""
    checks: dict = {}
    ready = True

    # Postgres
    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "connected"
    except Exception as e:
        checks["postgres"] = f"error: {e}"
        ready = False

    # Neo4j
    try:
        client = get_neo4j_client()
        ok = await client.verify_connectivity()
        checks["neo4j"] = "connected" if ok else "error"
        if not ok:
            ready = False
    except Exception as e:
        checks["neo4j"] = f"error: {e}"
        ready = False

    status_code = 200 if ready else 503
    return JSONResponse(
        content={"ready": ready, **checks},
        status_code=status_code,
    )


@router.get("/health/db", summary="PostgreSQL health")
async def health_db(db: AsyncSession = Depends(get_db)):
    """Verify PostgreSQL connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"postgres": "connected"}
    except Exception as e:
        return {"postgres": "error", "detail": str(e)}


@router.get("/health/neo4j", summary="Neo4j health")
async def health_neo4j():
    """Verify Neo4j graph database connectivity."""
    try:
        client = get_neo4j_client()
        ok = await client.verify_connectivity()
        return {"neo4j": "connected" if ok else "error"}
    except Exception as e:
        return {"neo4j": "error", "detail": str(e)}


@router.get("/health/openai", summary="LLM provider status")
async def health_openai(user: User | None = Depends(get_optional_current_user)):
    """Return current LLM provider configuration and whether an API key is available."""
    resolved = resolve_provider_settings(user)
    return {
        "openai_configured": resolved.configured,
        "model": resolved.model,
        "api_base": resolved.effective_api_base,
        "api_key_source": resolved.source,
        "has_user_api_key": resolved.has_user_api_key,
        "has_env_api_key": resolved.has_env_api_key,
    }
