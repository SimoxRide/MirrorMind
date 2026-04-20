"""Training Lab routes — interactive training to teach the clone about the user."""

import json
from uuid import UUID

from agents import Runner
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.definitions import training_analyst_agent, training_question_agent
from app.core.access import ensure_persona_access
from app.core.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.persona import Memory, PersonaCore, WritingSample
from app.models.policy import PolicyRule
from app.models.user import User
from app.schemas.persona import MemoryCreate, WritingSampleCreate
from app.services.provider_settings import resolve_provider_settings

logger = get_logger("training_lab")

router = APIRouter(prefix="/training", tags=["Training Lab"])


# ── Schemas ──────────────────────────────────────────────


class GenerateQuestionsRequest(BaseModel):
    persona_id: UUID
    count: int = Field(5, ge=1, le=20)
    categories: list[str] | None = None
    previous_questions: list[str] = Field(default_factory=list)


class TrainingQuestion(BaseModel):
    question: str
    category: str
    context_type: str
    scenario: str


class AnalyzeAnswerRequest(BaseModel):
    persona_id: UUID
    question: str
    category: str
    context_type: str
    answer: str
    auto_save: bool = True  # automatically save extracted data


class ExtractedWritingSample(BaseModel):
    content: str
    context_type: str
    tone: str | None = None
    notes: str | None = None


class ExtractedMemory(BaseModel):
    title: str
    content: str
    memory_type: str
    tags: list[str] | None = None
    linked_entities: list[str] | None = None


class ExtractedTrait(BaseModel):
    key: str
    value: str
    confidence: float


class ExtractedPolicy(BaseModel):
    name: str
    policy_type: str
    description: str


class AnalysisResult(BaseModel):
    writing_samples: list[ExtractedWritingSample] = []
    memories: list[ExtractedMemory] = []
    traits: list[ExtractedTrait] = []
    policies: list[ExtractedPolicy] = []
    summary: str = ""
    saved: bool = False
    saved_counts: dict[str, int] = {}


# ── Endpoints ────────────────────────────────────────────


@router.post("/generate-questions", response_model=list[TrainingQuestion])
async def generate_questions(
    req: GenerateQuestionsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate scenario-based training questions tailored to persona gaps."""
    persona = await ensure_persona_access(req.persona_id, user, db)
    provider_settings = resolve_provider_settings(user)
    if not provider_settings.configured:
        raise HTTPException(400, "Provider API key not configured")

    if not persona:
        raise HTTPException(404, "Persona not found")

    # Get existing memories to avoid duplicate topics
    mem_result = await db.execute(
        select(Memory.title, Memory.memory_type)
        .where(Memory.persona_id == req.persona_id)
        .limit(50)
    )
    existing_memories = [f"[{r[1]}] {r[0]}" for r in mem_result.all()]

    # Get existing writing sample count by context
    ws_result = await db.execute(
        select(WritingSample.context_type).where(
            WritingSample.persona_id == req.persona_id
        )
    )
    ws_contexts = [r[0] for r in ws_result.all()]
    context_counts = {}
    for c in ws_contexts:
        context_counts[c] = context_counts.get(c, 0) + 1

    prompt = f"""Persona: {persona.name}
Identity: {persona.identity_summary or 'Not defined yet'}

Existing memories ({len(existing_memories)} total):
{chr(10).join(existing_memories[:30]) if existing_memories else 'None yet'}

Writing samples per context: {json.dumps(context_counts) if context_counts else 'None yet'}

{"Focus on categories: " + ", ".join(req.categories) if req.categories else "Cover all categories evenly."}

{"PREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT THESE OR ASK SIMILAR ONES):" + chr(10) + chr(10).join(f"- {q}" for q in req.previous_questions) if req.previous_questions else ""}

Generate exactly {req.count} training questions. Focus on areas where the profile has GAPS.
Do NOT repeat or rephrase any of the previously asked questions."""

    try:
        result = await Runner.run(
            training_question_agent,
            input=prompt,
            run_config=provider_settings.to_run_config(),
        )
    except Exception as exc:
        logger.error("training_question_agent_failed", error=str(exc))
        raise HTTPException(502, "LLM agent failed to generate questions") from exc

    try:
        questions = json.loads(result.final_output)
        return [TrainingQuestion(**q) for q in questions]
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.error("Failed to parse training questions: %s", e)
        raise HTTPException(500, "Failed to generate questions")


@router.post("/analyze-answer", response_model=AnalysisResult)
async def analyze_answer(
    req: AnalyzeAnswerRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Analyze a user's answer to extract clone knowledge and optionally auto-save."""
    persona = await ensure_persona_access(req.persona_id, user, db)
    provider_settings = resolve_provider_settings(user)
    if not provider_settings.configured:
        raise HTTPException(400, "Provider API key not configured")

    if not persona:
        raise HTTPException(404, "Persona not found")

    # Get existing memory titles to avoid exact duplicates
    mem_result = await db.execute(
        select(Memory.title).where(Memory.persona_id == req.persona_id)
    )
    existing_titles = [r[0] for r in mem_result.all()]

    prompt = f"""SCENARIO QUESTION ({req.category}, context: {req.context_type}):
{req.question}

PERSON'S ANSWER:
{req.answer}

CURRENT PERSONA:
Name: {persona.name}
Identity: {persona.identity_summary or 'Not defined yet'}

EXISTING MEMORY TITLES (avoid duplicates):
{chr(10).join(existing_titles[:40]) if existing_titles else 'None yet'}

Analyze the answer thoroughly and extract all useful data for the clone."""

    try:
        result = await Runner.run(
            training_analyst_agent,
            input=prompt,
            run_config=provider_settings.to_run_config(),
        )
    except Exception as exc:
        logger.error("training_analyst_agent_failed", error=str(exc))
        raise HTTPException(502, "LLM agent failed to analyze answer") from exc

    try:
        data = json.loads(result.final_output)
    except (json.JSONDecodeError, TypeError):
        logger.error("Failed to parse analysis: %s", result.final_output)
        raise HTTPException(500, "Failed to analyze answer")

    analysis = AnalysisResult(
        writing_samples=[
            ExtractedWritingSample(**ws) for ws in data.get("writing_samples", [])
        ],
        memories=[ExtractedMemory(**m) for m in data.get("memories", [])],
        traits=[ExtractedTrait(**t) for t in data.get("traits", [])],
        policies=[ExtractedPolicy(**p) for p in data.get("policies", [])],
        summary=data.get("summary", ""),
    )

    # Auto-save if requested
    if req.auto_save:
        saved_counts = {
            "writing_samples": 0,
            "memories": 0,
            "policies": 0,
            "skipped_duplicates": 0,
        }

        # Get existing writing sample contents for dedup
        ws_result = await db.execute(
            select(WritingSample.content).where(
                WritingSample.persona_id == req.persona_id
            )
        )
        existing_ws_contents = {r[0].strip().lower() for r in ws_result.all()}

        # Get existing policy names for dedup
        pol_result = await db.execute(
            select(PolicyRule.name).where(PolicyRule.persona_id == req.persona_id)
        )
        existing_policy_names = {r[0].strip().lower() for r in pol_result.all()}

        for ws in analysis.writing_samples:
            if ws.content.strip().lower() in existing_ws_contents:
                saved_counts["skipped_duplicates"] += 1
                continue
            sample = WritingSample(
                persona_id=req.persona_id,
                content=ws.content,
                context_type=ws.context_type,
                tone=ws.tone,
                notes=ws.notes,
                is_representative=True,
            )
            db.add(sample)
            saved_counts["writing_samples"] += 1

        for mem in analysis.memories:
            # Skip if very similar title exists
            if mem.title in existing_titles:
                saved_counts["skipped_duplicates"] += 1
                continue
            memory = Memory(
                persona_id=req.persona_id,
                memory_type=mem.memory_type,
                title=mem.title,
                content=mem.content,
                source="training_lab",
                tags=mem.tags or [],
                linked_entities=mem.linked_entities or [],
            )
            db.add(memory)
            saved_counts["memories"] += 1

        for pol in analysis.policies:
            if pol.name.strip().lower() in existing_policy_names:
                saved_counts["skipped_duplicates"] += 1
                continue
            policy = PolicyRule(
                persona_id=req.persona_id,
                policy_type=pol.policy_type,
                name=pol.name,
                description=pol.description,
                priority=0,
            )
            db.add(policy)
            saved_counts["policies"] += 1

        await db.flush()
        analysis.saved = True
        analysis.saved_counts = saved_counts

    return analysis
