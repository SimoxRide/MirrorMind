"""CRUD service for MemoryImage."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_image import MemoryImage


class MemoryImageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        persona_id: UUID,
        kind: str,
        title: str,
        caption: str | None,
        content_type: str,
        file_name: str | None,
        data: bytes,
        memory_id: UUID | None = None,
        tags: list[str] | None = None,
    ) -> MemoryImage:
        image = MemoryImage(
            persona_id=persona_id,
            kind=kind,
            title=title or (file_name or "image"),
            caption=caption,
            content_type=content_type or "image/jpeg",
            file_name=file_name,
            size_bytes=len(data),
            data=data,
            memory_id=memory_id,
            tags=tags or [],
            analysis_status="pending",
            analysis={},
        )
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return image

    async def get(self, image_id: UUID) -> MemoryImage | None:
        return await self.db.get(MemoryImage, image_id)

    async def list_by_persona(
        self,
        persona_id: UUID,
        *,
        kind: str | None = None,
        memory_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryImage]:
        stmt = (
            select(MemoryImage)
            .where(MemoryImage.persona_id == persona_id)
            .order_by(MemoryImage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if kind:
            stmt = stmt.where(MemoryImage.kind == kind)
        if memory_id:
            stmt = stmt.where(MemoryImage.memory_id == memory_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_persona(
        self,
        persona_id: UUID,
        *,
        kind: str | None = None,
        memory_id: UUID | None = None,
    ) -> int:
        stmt = select(func.count(MemoryImage.id)).where(
            MemoryImage.persona_id == persona_id
        )
        if kind:
            stmt = stmt.where(MemoryImage.kind == kind)
        if memory_id:
            stmt = stmt.where(MemoryImage.memory_id == memory_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def update(self, image_id: UUID, data: dict) -> MemoryImage | None:
        image = await self.get(image_id)
        if not image:
            return None
        for field, value in data.items():
            setattr(image, field, value)
        await self.db.flush()
        await self.db.refresh(image)
        return image

    async def delete(self, image_id: UUID) -> bool:
        image = await self.get(image_id)
        if not image:
            return False
        await self.db.delete(image)
        await self.db.flush()
        return True
