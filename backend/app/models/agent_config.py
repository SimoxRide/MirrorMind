"""Agent configuration model — prompt/model/retrieval settings."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_configs"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_cores.id"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # persona_synthesizer, interview, style_analysis, graph_memory,
    # response_generator, critic, evaluation

    system_prompt: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(100), default="gpt-4o")
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    retrieval_settings: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    guardrails: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
