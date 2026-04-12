"""Writing sample service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona import WritingSample
from app.schemas.persona import WritingSampleCreate


class WritingSampleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: WritingSampleCreate) -> WritingSample:
        sample = WritingSample(**data.model_dump(exclude_none=True))
        self.db.add(sample)
        await self.db.flush()
        await self.db.refresh(sample)
        return sample

    async def list_by_persona(
        self,
        persona_id: UUID,
        *,
        context_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WritingSample]:
        stmt = (
            select(WritingSample)
            .where(WritingSample.persona_id == persona_id)
            .order_by(WritingSample.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if context_type:
            stmt = stmt.where(WritingSample.context_type == context_type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_persona(
        self, persona_id: UUID, *, context_type: str | None = None
    ) -> int:
        stmt = select(func.count(WritingSample.id)).where(
            WritingSample.persona_id == persona_id
        )
        if context_type:
            stmt = stmt.where(WritingSample.context_type == context_type)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get(self, sample_id: UUID) -> WritingSample | None:
        return await self.db.get(WritingSample, sample_id)

    async def delete(self, sample_id: UUID) -> bool:
        sample = await self.get(sample_id)
        if not sample:
            return False
        await self.db.delete(sample)
        await self.db.flush()
        return True

    async def update(self, sample_id: UUID, data: dict) -> WritingSample | None:
        sample = await self.get(sample_id)
        if not sample:
            return None
        for field, value in data.items():
            setattr(sample, field, value)
        await self.db.flush()
        await self.db.refresh(sample)
        return sample
