"""MemoryImage SQLAlchemy model.

Stores images attached to a persona to enrich the clone's knowledge:
- ``kind='memory'`` — a scene/photo the persona remembers (optionally linked
  to a specific ``Memory`` record).
- ``kind='person'`` — a photo depicting a person in the persona's life
  (spouse, friend, colleague, family member, pet, ...).
- ``kind='self'`` — a photo of the persona themselves; its automatic analysis
  can seed additional identity details on the clone.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MemoryImage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memory_images"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persona_cores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to a specific Memory record (e.g. an episodic memory).
    memory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # self | memory | person
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="memory")

    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw bytes of the image; mime_type tells the browser how to render.
    content_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="image/jpeg"
    )
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Populated by the vision-analysis pipeline.
    analysis_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | ready | failed | skipped
    analysis: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    tags: Mapped[list | None] = mapped_column(JSONB, default=list)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    persona = relationship("PersonaCore", backref="images", lazy="selectin")
    memory = relationship("Memory", lazy="selectin")
