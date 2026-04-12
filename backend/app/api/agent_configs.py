"""Agent config routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.agent_config import AgentConfig
from app.schemas.core import AgentConfigCreate, AgentConfigRead, AgentConfigUpdate

router = APIRouter(prefix="/agent-configs", tags=["Agent Config"])


@router.post("/", response_model=AgentConfigRead, status_code=201)
async def create_config(data: AgentConfigCreate, db: AsyncSession = Depends(get_db)):
    config = AgentConfig(**data.model_dump(exclude_none=True))
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


@router.get("/", response_model=list[AgentConfigRead])
async def list_configs(
    persona_id: UUID = Query(...), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(AgentConfig)
        .where(AgentConfig.persona_id == persona_id)
        .order_by(AgentConfig.agent_name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{config_id}", response_model=AgentConfigRead)
async def get_config(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(AgentConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent config not found")
    return config


@router.patch("/{config_id}", response_model=AgentConfigRead)
async def update_config(
    config_id: UUID, data: AgentConfigUpdate, db: AsyncSession = Depends(get_db)
):
    config = await db.get(AgentConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent config not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    await db.flush()
    await db.refresh(config)
    return config
