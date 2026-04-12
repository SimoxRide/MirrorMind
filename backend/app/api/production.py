"""Production clone management and public chat endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.persona import PersonaCore
from app.models.production import (
    ProductionClone,
    _generate_api_key,
    _generate_endpoint_id,
)
from app.schemas.core import CloneRequest, CloneResponse
from app.services.clone_engine import CloneEngine

router = APIRouter(tags=["Production"])


# ── Schemas ──────────────────────────────────────────────


class ActivateRequest(BaseModel):
    persona_id: UUID
    require_api_key: bool = True


class ProductionCloneOut(BaseModel):
    id: str
    persona_id: str
    persona_name: str
    endpoint_id: str
    is_active: bool
    require_api_key: bool
    api_key: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class PublicChatRequest(BaseModel):
    message: str
    context_type: str = "general"
    conversation_history: list[dict] | None = None


# ── Admin endpoints (require admin token) ────────────────


@router.get("/production/clones", response_model=list[ProductionCloneOut])
async def list_production_clones(
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductionClone).order_by(ProductionClone.created_at.desc())
    )
    clones = result.scalars().all()
    return [
        ProductionCloneOut(
            id=str(c.id),
            persona_id=str(c.persona_id),
            persona_name=c.persona_name,
            endpoint_id=c.endpoint_id,
            is_active=c.is_active,
            require_api_key=c.require_api_key,
            api_key=c.api_key,
            created_at=c.created_at.isoformat(),
        )
        for c in clones
    ]


@router.post("/production/clones", response_model=ProductionCloneOut, status_code=201)
async def activate_production_clone(
    data: ActivateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Check persona exists
    persona = await db.get(PersonaCore, data.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found.")

    # Check if already deployed
    existing = await db.execute(
        select(ProductionClone).where(ProductionClone.persona_id == data.persona_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Persona already has an active production clone."
        )

    api_key = _generate_api_key() if data.require_api_key else None

    clone = ProductionClone(
        persona_id=data.persona_id,
        persona_name=persona.name,
        endpoint_id=_generate_endpoint_id(),
        require_api_key=data.require_api_key,
        api_key=api_key,
    )
    db.add(clone)
    await db.flush()
    await db.refresh(clone)

    return ProductionCloneOut(
        id=str(clone.id),
        persona_id=str(clone.persona_id),
        persona_name=clone.persona_name,
        endpoint_id=clone.endpoint_id,
        is_active=clone.is_active,
        require_api_key=clone.require_api_key,
        api_key=clone.api_key,
        created_at=clone.created_at.isoformat(),
    )


@router.delete("/production/clones/{clone_id}", status_code=204)
async def deactivate_production_clone(
    clone_id: UUID,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    clone = await db.get(ProductionClone, clone_id)
    if not clone:
        raise HTTPException(status_code=404, detail="Production clone not found.")
    await db.delete(clone)


@router.post(
    "/production/clones/{clone_id}/regenerate-key", response_model=ProductionCloneOut
)
async def regenerate_api_key(
    clone_id: UUID,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    clone = await db.get(ProductionClone, clone_id)
    if not clone:
        raise HTTPException(status_code=404, detail="Production clone not found.")
    if not clone.require_api_key:
        raise HTTPException(
            status_code=400, detail="This clone does not require an API key."
        )

    clone.api_key = _generate_api_key()
    await db.flush()
    await db.refresh(clone)

    return ProductionCloneOut(
        id=str(clone.id),
        persona_id=str(clone.persona_id),
        persona_name=clone.persona_name,
        endpoint_id=clone.endpoint_id,
        is_active=clone.is_active,
        require_api_key=clone.require_api_key,
        api_key=clone.api_key,
        created_at=clone.created_at.isoformat(),
    )


# ── Public chat endpoint (no admin auth — API key optional) ──


@router.post("/production/chat/{endpoint_id}", response_model=CloneResponse)
async def public_clone_chat(
    endpoint_id: str,
    data: PublicChatRequest,
    db: AsyncSession = Depends(get_db),
    x_api_key: str | None = Header(None),
):
    result = await db.execute(
        select(ProductionClone).where(
            ProductionClone.endpoint_id == endpoint_id,
            ProductionClone.is_active == True,  # noqa: E712
        )
    )
    clone = result.scalar_one_or_none()
    if not clone:
        raise HTTPException(status_code=404, detail="Clone not found or inactive.")

    # API key verification
    if clone.require_api_key:
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required. Pass it via X-API-Key header.",
            )
        if not _constant_time_compare(x_api_key, clone.api_key or ""):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key.",
            )

    engine = CloneEngine(db)
    req = CloneRequest(
        persona_id=clone.persona_id,
        message=data.message,
        context_type=data.context_type,
        conversation_history=data.conversation_history,
    )
    return await engine.generate(req)


def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    import hmac

    return hmac.compare_digest(a.encode(), b.encode())
