"""Extension service — CRUD + platform-specific helpers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_credentials, encrypt_credentials, is_encrypted
from app.models.extension import Extension


def _decrypt(ext: Extension | None) -> Extension | None:
    """In-place decrypt credentials when returning an Extension to callers."""
    if ext is None:
        return None
    if is_encrypted(ext.credentials):
        ext.credentials = decrypt_credentials(ext.credentials)
    return ext


class ExtensionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_persona(self, persona_id: UUID) -> list[Extension]:
        result = await self.db.execute(
            select(Extension)
            .where(Extension.persona_id == persona_id)
            .order_by(Extension.created_at.desc())
        )
        exts = list(result.scalars().all())
        for ext in exts:
            _decrypt(ext)
        return exts

    async def get(self, ext_id: UUID) -> Extension | None:
        return _decrypt(await self.db.get(Extension, ext_id))

    async def create(self, data: dict) -> Extension:
        payload = dict(data)
        if "credentials" in payload:
            payload["credentials"] = encrypt_credentials(payload.get("credentials"))
        ext = Extension(**payload)
        self.db.add(ext)
        await self.db.flush()
        await self.db.refresh(ext)
        return _decrypt(ext)

    async def update(self, ext: Extension, data: dict) -> Extension:
        for key, val in data.items():
            if val is None:
                continue
            if key == "credentials":
                setattr(ext, key, encrypt_credentials(val))
            else:
                setattr(ext, key, val)
        await self.db.flush()
        await self.db.refresh(ext)
        return _decrypt(ext)

    async def delete(self, ext: Extension) -> None:
        await self.db.delete(ext)
        await self.db.flush()
