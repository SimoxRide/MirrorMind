"""Policy rules — versioned behavioral constraints for the clone."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PolicyRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "policy_rules"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_cores.id"), nullable=False, index=True
    )
    policy_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Types: tone, risk_tolerance, escalation, flirting, work_communication,
    #        conflict_handling, uncertainty, forbidden_pattern, ask_before_send,
    #        human_review_required

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    actions: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
