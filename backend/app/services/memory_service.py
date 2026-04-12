"""Memory service — CRUD for all memory types."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona import Memory
from app.schemas.persona import MemoryCreate, MemoryUpdate


class MemoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: MemoryCreate) -> Memory:
        memory = Memory(**data.model_dump(exclude_none=True))
        self.db.add(memory)
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def get(self, memory_id: UUID) -> Memory | None:
        return await self.db.get(Memory, memory_id)

    async def list_by_persona(
        self,
        persona_id: UUID,
        *,
        memory_type: str | None = None,
        approval_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.persona_id == persona_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)
        if approval_status:
            stmt = stmt.where(Memory.approval_status == approval_status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_persona(
        self,
        persona_id: UUID,
        *,
        memory_type: str | None = None,
        approval_status: str | None = None,
    ) -> int:
        stmt = select(func.count(Memory.id)).where(Memory.persona_id == persona_id)
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)
        if approval_status:
            stmt = stmt.where(Memory.approval_status == approval_status)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def update(self, memory_id: UUID, data: MemoryUpdate) -> Memory | None:
        memory = await self.get(memory_id)
        if not memory:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(memory, field, value)
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def delete(self, memory_id: UUID) -> bool:
        memory = await self.get(memory_id)
        if not memory:
            return False
        await self.db.delete(memory)
        await self.db.flush()
        return True
