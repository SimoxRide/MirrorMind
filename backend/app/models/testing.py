"""Testing & evaluation models — scenarios, results, evaluations."""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TestScenario(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "test_scenarios"

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_cores.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    context_type: Mapped[str] = mapped_column(String(100), default="general")
    # friend, romantic, work, conflict, adversarial, boundary, etc.
    test_mode: Mapped[str] = mapped_column(String(50), default="single")
    # single, multi_turn, adversarial, boundary, tone_fidelity, memory_recall, policy_compliance

    input_message: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_history: Mapped[list | None] = mapped_column(JSONB, default=list)
    gold_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationship_info: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    results: Mapped[list["TestResult"]] = relationship(
        back_populates="scenario", lazy="selectin"
    )


class TestResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "test_results"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_scenarios.id"), nullable=False, index=True
    )
    clone_response: Mapped[str] = mapped_column(Text, nullable=False)
    variant_index: Mapped[int] = mapped_column(Integer, default=0)
    trace: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    # trace contains: retrieved memories, graph nodes, policies applied, agent steps
    generation_config: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    scenario: Mapped["TestScenario"] = relationship(back_populates="results")
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="test_result", lazy="selectin"
    )


class Evaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evaluations"

    test_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_results.id"), nullable=False, index=True
    )

    # --- scores (0.0–1.0) ---
    style_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    tone_fidelity: Mapped[float | None] = mapped_column(Float, nullable=True)
    persona_consistency: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_compliance: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    artificiality: Mapped[float | None] = mapped_column(Float, nullable=True)
    emotional_appropriateness: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    boundary_respect: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_usefulness: Mapped[float | None] = mapped_column(Float, nullable=True)

    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # pass, fail, mixed
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbs: Mapped[str | None] = mapped_column(String(10), nullable=True)  # up, down

    test_result: Mapped["TestResult"] = relationship(back_populates="evaluations")
