"""Agent config routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import ensure_persona_access
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.agent_config import AgentConfig
from app.models.user import User
from app.schemas.core import AgentConfigCreate, AgentConfigRead, AgentConfigUpdate

router = APIRouter(prefix="/agent-configs", tags=["Agent Config"])


@router.post("/", response_model=AgentConfigRead, status_code=201)
async def create_config(
    data: AgentConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await ensure_persona_access(data.persona_id, user, db)
    config = AgentConfig(**data.model_dump(exclude_none=True))
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


@router.get("/", response_model=list[AgentConfigRead])
async def list_configs(
    response: Response,
    persona_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await ensure_persona_access(persona_id, user, db)
    base = select(AgentConfig).where(AgentConfig.persona_id == persona_id)
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    stmt = base.order_by(AgentConfig.agent_name).limit(limit).offset(offset)
    result = await db.execute(stmt)
    response.headers["X-Total-Count"] = str(total)
    return list(result.scalars().all())


@router.get("/{config_id}", response_model=AgentConfigRead)
async def get_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    config = await db.get(AgentConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent config not found")
    await ensure_persona_access(config.persona_id, user, db)
    return config


@router.patch("/{config_id}", response_model=AgentConfigRead)
async def update_config(
    config_id: UUID,
    data: AgentConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    config = await db.get(AgentConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent config not found")
    await ensure_persona_access(config.persona_id, user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    await db.flush()
    await db.refresh(config)
    return config
