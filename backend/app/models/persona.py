"""PersonaCore SQLAlchemy model — the identity definition of the virtual clone."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PersonaCore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "persona_cores"

    # --- identity ---
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    identity_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- structured persona fields stored as JSONB ---
    values: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    tone: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    humor_style: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    communication_preferences: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    emotional_patterns: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # --- mode-specific behaviors ---
    modes: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    # expected shape: {"work": {...}, "romantic": {...}, "friend": {...}, "conflict": {...}}

    # --- boundaries ---
    never_say: Mapped[list | None] = mapped_column(JSONB, default=list)
    avoid_topics: Mapped[list | None] = mapped_column(JSONB, default=list)
    ask_before_acting: Mapped[list | None] = mapped_column(JSONB, default=list)

    # --- autonomy ---
    confidence_threshold: Mapped[float | None] = mapped_column(default=0.7)
    autonomy_level: Mapped[str] = mapped_column(String(50), default="medium")

    # --- relationships ---
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="persona", lazy="selectin"
    )
    writing_samples: Mapped[list["WritingSample"]] = relationship(
        back_populates="persona", lazy="selectin"
    )


class Memory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memories"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persona_cores.id"),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Types: long_term, episodic, relational, preference, project, style, decision

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), default="manual")
    confidence: Mapped[float] = mapped_column(default=1.0)
    date_start: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_end: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONB, default=list)
    linked_entities: Mapped[list | None] = mapped_column(JSONB, default=list)
    approval_status: Mapped[str] = mapped_column(
        String(20), default="approved"
    )  # approved, pending, rejected
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    persona: Mapped["PersonaCore"] = relationship(back_populates="memories")


class WritingSample(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "writing_samples"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persona_cores.id"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context_type: Mapped[str] = mapped_column(String(100), default="general")
    target_person_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emotional_intensity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_representative: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # --- extracted style features (populated by analysis pipeline) ---
    style_features: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    persona: Mapped["PersonaCore"] = relationship(back_populates="writing_samples")
