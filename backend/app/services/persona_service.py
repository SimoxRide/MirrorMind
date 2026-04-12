"""Persona service — business logic for PersonaCore CRUD."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona import PersonaCore
from app.schemas.persona import PersonaCoreCreate, PersonaCoreUpdate


class PersonaService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: PersonaCoreCreate) -> PersonaCore:
        persona = PersonaCore(**data.model_dump(exclude_none=True))
        self.db.add(persona)
        await self.db.flush()
        await self.db.refresh(persona)
        return persona

    async def get(self, persona_id: UUID) -> PersonaCore | None:
        return await self.db.get(PersonaCore, persona_id)

    async def list_all(self, *, active_only: bool = True) -> list[PersonaCore]:
        stmt = select(PersonaCore).order_by(PersonaCore.created_at.desc())
        if active_only:
            stmt = stmt.where(PersonaCore.is_active.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
        return persona

    async def delete(self, persona_id: UUID) -> bool:
        persona = await self.get(persona_id)
        if not persona:
            return False
        persona.is_active = False
        await self.db.flush()
        return True
