"""ProductionClone model — tracks deployed AI clones with optional API key auth."""

import secrets
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _generate_endpoint_id() -> str:
    return secrets.token_urlsafe(16)


def _generate_api_key() -> str:
    return f"mm_{secrets.token_urlsafe(32)}"


class ProductionClone(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "production_clones"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persona_cores.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    endpoint_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        default=_generate_endpoint_id,
    )
    persona_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_api_key: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
