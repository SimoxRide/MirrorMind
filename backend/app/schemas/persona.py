"""Pydantic v2 schemas for PersonaCore, Memory, WritingSample."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── PersonaCore ──────────────────────────────────────────


class PersonaCoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    identity_summary: str = Field("", max_length=5000)
    values: dict | None = None
    tone: dict | None = None
    humor_style: dict | None = None
    communication_preferences: dict | None = None
    emotional_patterns: dict | None = None
    modes: dict | None = None
    never_say: list[str] | None = None
    avoid_topics: list[str] | None = None
    ask_before_acting: list[str] | None = None
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)
    autonomy_level: str = Field("medium", pattern=r"^(low|medium|high)$")


class PersonaCoreUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    identity_summary: str | None = Field(None, max_length=5000)
    values: dict | None = None
    tone: dict | None = None
    humor_style: dict | None = None
    communication_preferences: dict | None = None
    emotional_patterns: dict | None = None
    modes: dict | None = None
    never_say: list[str] | None = None
    avoid_topics: list[str] | None = None
    ask_before_acting: list[str] | None = None
    confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)
    autonomy_level: str | None = Field(None, pattern=r"^(low|medium|high)$")


class PersonaCoreRead(BaseModel):
    id: UUID
    name: str
    identity_summary: str
    version: int
    is_active: bool
    values: dict | None
    tone: dict | None
    humor_style: dict | None
    communication_preferences: dict | None
    emotional_patterns: dict | None
    modes: dict | None
    never_say: list | None
    avoid_topics: list | None
    ask_before_acting: list | None
    confidence_threshold: float | None
    autonomy_level: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Memory ───────────────────────────────────────────────


class MemoryCreate(BaseModel):
    persona_id: UUID
    memory_type: str = Field(
        ...,
        pattern=r"^(long_term|episodic|relational|preference|project|style|decision)$",
    )
    title: str = Field(..., min_length=1, max_length=500)
    content: str
    source: str = "manual"
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    date_start: str | None = None
    date_end: str | None = None
    tags: list[str] | None = None
    linked_entities: list[str] | None = None
    approval_status: str = "approved"
    metadata_extra: dict | None = None


class MemoryUpdate(BaseModel):
    memory_type: str | None = None
    title: str | None = None
    content: str | None = None
    source: str | None = None
    confidence: float | None = None
    date_start: str | None = None
    date_end: str | None = None
    tags: list[str] | None = None
    linked_entities: list[str] | None = None
    approval_status: str | None = None
    metadata_extra: dict | None = None


class MemoryRead(BaseModel):
    id: UUID
    persona_id: UUID
    memory_type: str
    title: str
    content: str
    source: str
    confidence: float
    date_start: str | None
    date_end: str | None
    tags: list | None
    linked_entities: list | None
    approval_status: str
    metadata_extra: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── WritingSample ────────────────────────────────────────


class WritingSampleCreate(BaseModel):
    persona_id: UUID
    content: str = Field(..., min_length=1)
    context_type: str = "general"
    target_person_type: str | None = None
    emotional_intensity: str | None = None
    tone: str | None = None
    is_representative: bool = True
    notes: str | None = None
    metadata_extra: dict | None = None


class WritingSampleUpdate(BaseModel):
    content: str | None = None
    context_type: str | None = None
    target_person_type: str | None = None
    emotional_intensity: str | None = None
    tone: str | None = None
    is_representative: bool | None = None
    notes: str | None = None
    metadata_extra: dict | None = None


class WritingSampleRead(BaseModel):
    id: UUID
    persona_id: UUID
    content: str
    context_type: str
    target_person_type: str | None
    emotional_intensity: str | None
    tone: str | None
    is_representative: bool
    notes: str | None
    style_features: dict | None
    metadata_extra: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
