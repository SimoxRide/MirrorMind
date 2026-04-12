"""Interview models — guided questionnaire sessions."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InterviewSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_cores.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Untitled Session")
    status: Mapped[str] = mapped_column(
        String(30), default="in_progress"
    )  # in_progress, completed
    question_count: Mapped[int] = mapped_column(Integer, default=0)

    answers: Mapped[list["InterviewAnswer"]] = relationship(
        back_populates="session",
        lazy="selectin",
        order_by="InterviewAnswer.order_index",
    )


class InterviewAnswer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_answers"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extracted_traits: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    trait_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["InterviewSession"] = relationship(back_populates="answers")
