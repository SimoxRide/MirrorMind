"""Pydantic schemas for MemoryImage."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

ImageKind = str  # "self" | "memory" | "person"


class MemoryImageRead(BaseModel):
    id: UUID
    persona_id: UUID
    memory_id: UUID | None
    kind: str
    title: str
    caption: str | None
    content_type: str
    file_name: str | None
    size_bytes: int
    analysis_status: str
    analysis: dict | None
    tags: list | None
    metadata_extra: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryImageUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    caption: str | None = None
    kind: str | None = Field(None, pattern=r"^(self|memory|person)$")
    memory_id: UUID | None = None
    tags: list[str] | None = None
    metadata_extra: dict | None = None


class MemoryImageAnalyzeResult(BaseModel):
    image: MemoryImageRead
    persona_updated: bool = False
    memory_created_id: UUID | None = None
