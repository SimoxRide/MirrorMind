"""Persona service — business logic for PersonaCore CRUD."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_persona, persona_cache
from app.models.persona import PersonaCore
from app.schemas.persona import PersonaCoreCreate, PersonaCoreUpdate


class PersonaService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, data: PersonaCoreCreate, *, owner_id: UUID | None = None
    ) -> PersonaCore:
        payload = data.model_dump(exclude_none=True)
        if owner_id is not None:
            payload["owner_id"] = owner_id
        persona = PersonaCore(**payload)
        self.db.add(persona)
        await self.db.flush()
        await self.db.refresh(persona)
        return persona

    async def get(self, persona_id: UUID) -> PersonaCore | None:
        key = str(persona_id)
        cached = persona_cache.get(key)
        if cached is not None:
            return cached
        persona = await self.db.get(PersonaCore, persona_id)
        if persona is not None:
            persona_cache[key] = persona
        return persona

    async def list_all(
        self,
        *,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PersonaCore], int]:
        base = select(PersonaCore)
        if active_only:
            base = base.where(PersonaCore.is_active.is_(True))
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(PersonaCore.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def list_for_owner(
        self,
        owner_id: UUID,
        *,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PersonaCore], int]:
        base = select(PersonaCore).where(
            (PersonaCore.owner_id == owner_id) | (PersonaCore.owner_id.is_(None))
        )
        if active_only:
            base = base.where(PersonaCore.is_active.is_(True))
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(PersonaCore.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update(
        self, persona_id: UUID, data: PersonaCoreUpdate
    ) -> PersonaCore | None:
        persona = await self.get(persona_id)
        if not persona:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(persona, field, value)
        persona.version += 1
        await self.db.flush()
        await self.db.refresh(persona)
        invalidate_persona(persona_id)
        return persona

    async def delete(self, persona_id: UUID) -> bool:
        persona = await self.get(persona_id)
        if not persona:
            return False
        persona.is_active = False
        await self.db.flush()
        invalidate_persona(persona_id)
        return True
