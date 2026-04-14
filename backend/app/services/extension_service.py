"""Extension service — CRUD + platform-specific helpers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extension import Extension


class ExtensionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_persona(self, persona_id: UUID) -> list[Extension]:
        result = await self.db.execute(
            select(Extension)
            .where(Extension.persona_id == persona_id)
            .order_by(Extension.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, ext_id: UUID) -> Extension | None:
        return await self.db.get(Extension, ext_id)

    async def create(self, data: dict) -> Extension:
        ext = Extension(**data)
        self.db.add(ext)
        await self.db.flush()
        await self.db.refresh(ext)
        return ext

    async def update(self, ext: Extension, data: dict) -> Extension:
        for key, val in data.items():
            if val is not None:
                setattr(ext, key, val)
        await self.db.flush()
        await self.db.refresh(ext)
        return ext

    async def delete(self, ext: Extension) -> None:
        await self.db.delete(ext)
        await self.db.flush()
