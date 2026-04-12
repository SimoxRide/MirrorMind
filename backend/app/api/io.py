"""Import / Export routes — persona bundles, memories, graph snapshots."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.agent_config import AgentConfig
from app.models.interview import InterviewAnswer, InterviewSession
from app.models.persona import Memory, PersonaCore, WritingSample
from app.models.policy import PolicyRule
from app.models.testing import TestScenario

router = APIRouter(prefix="/io", tags=["Import / Export"])


@router.get("/export/persona/{persona_id}")
async def export_persona_bundle(persona_id: UUID, db: AsyncSession = Depends(get_db)):
    """Export full persona bundle as JSON."""
    persona = await db.get(PersonaCore, persona_id)
    if not persona:
        return ORJSONResponse({"error": "Persona not found"}, status_code=404)

    # Memories
    mem_result = await db.execute(select(Memory).where(Memory.persona_id == persona_id))
    memories = mem_result.scalars().all()

    # Writing samples
    ws_result = await db.execute(
        select(WritingSample).where(WritingSample.persona_id == persona_id)
    )
    samples = ws_result.scalars().all()

    # Policies
    pol_result = await db.execute(
        select(PolicyRule).where(PolicyRule.persona_id == persona_id)
    )
    policies = pol_result.scalars().all()

    # Scenarios
    sc_result = await db.execute(
        select(TestScenario).where(TestScenario.persona_id == persona_id)
    )
    scenarios = sc_result.scalars().all()

    from app.schemas.persona import PersonaCoreRead, MemoryRead, WritingSampleRead
    from app.schemas.core import PolicyRuleRead, TestScenarioRead

    bundle = {
        "persona": PersonaCoreRead.model_validate(persona).model_dump(mode="json"),
        "memories": [
            MemoryRead.model_validate(m).model_dump(mode="json") for m in memories
        ],
        "writing_samples": [
            WritingSampleRead.model_validate(s).model_dump(mode="json") for s in samples
        ],
        "policies": [
            PolicyRuleRead.model_validate(p).model_dump(mode="json") for p in policies
        ],
        "test_scenarios": [
            TestScenarioRead.model_validate(s).model_dump(mode="json")
            for s in scenarios
        ],
    }
    return ORJSONResponse(bundle)


@router.post("/import/persona")
async def import_persona_bundle(bundle: dict, db: AsyncSession = Depends(get_db)):
    """Import a persona bundle from JSON.

    This creates a new persona with new UUIDs, preserving content.
    """
    from app.schemas.persona import PersonaCoreCreate, MemoryCreate, WritingSampleCreate

    persona_data = bundle.get("persona", {})
    persona = PersonaCore(
        name=persona_data.get("name", "Imported Persona"),
        identity_summary=persona_data.get("identity_summary", ""),
        values=persona_data.get("values"),
        tone=persona_data.get("tone"),
        humor_style=persona_data.get("humor_style"),
        communication_preferences=persona_data.get("communication_preferences"),
        emotional_patterns=persona_data.get("emotional_patterns"),
        modes=persona_data.get("modes"),
        never_say=persona_data.get("never_say"),
        avoid_topics=persona_data.get("avoid_topics"),
        ask_before_acting=persona_data.get("ask_before_acting"),
        confidence_threshold=persona_data.get("confidence_threshold", 0.7),
        autonomy_level=persona_data.get("autonomy_level", "medium"),
    )
    db.add(persona)
    await db.flush()

    counts = {"memories": 0, "writing_samples": 0, "policies": 0}

    for mem_data in bundle.get("memories", []):
        mem = Memory(
            persona_id=persona.id,
            memory_type=mem_data.get("memory_type", "long_term"),
            title=mem_data.get("title", ""),
            content=mem_data.get("content", ""),
            source=mem_data.get("source", "import"),
            confidence=mem_data.get("confidence", 1.0),
            tags=mem_data.get("tags"),
            linked_entities=mem_data.get("linked_entities"),
        )
        db.add(mem)
        counts["memories"] += 1

    for ws_data in bundle.get("writing_samples", []):
        ws = WritingSample(
            persona_id=persona.id,
            content=ws_data.get("content", ""),
            context_type=ws_data.get("context_type", "general"),
            target_person_type=ws_data.get("target_person_type"),
            tone=ws_data.get("tone"),
            is_representative=ws_data.get("is_representative", True),
        )
        db.add(ws)
        counts["writing_samples"] += 1

    for pol_data in bundle.get("policies", []):
        pol = PolicyRule(
            persona_id=persona.id,
            policy_type=pol_data.get("policy_type", "tone"),
            name=pol_data.get("name", ""),
            description=pol_data.get("description", ""),
            conditions=pol_data.get("conditions"),
            actions=pol_data.get("actions"),
        )
        db.add(pol)
        counts["policies"] += 1

    await db.flush()

    return {
        "status": "ok",
        "persona_id": str(persona.id),
        "imported": counts,
    }


# ── Quick Import (ChatGPT JSON) ─────────────────────────


class QuickImportMemory(BaseModel):
    memory_type: str = Field(
        "long_term",
        pattern=r"^(long_term|episodic|relational|preference|project|style|decision)$",
    )
    title: str = Field(..., min_length=1, max_length=500)
    content: str
    tags: list[str] | None = None


class QuickImportWritingSample(BaseModel):
    content: str
    context_type: str = "general"
    tone: str | None = None


class QuickImportPolicy(BaseModel):
    policy_type: str = "tone"
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class QuickImportPersonaUpdate(BaseModel):
    identity_summary: str | None = None
    values: dict | None = None
    communication_preferences: dict | None = None
    tone: dict | None = None
    humor_style: dict | None = None
    emotional_patterns: dict | None = None
    never_say: list[str] | None = None
    avoid_topics: list[str] | None = None


class QuickImportPayload(BaseModel):
    persona_id: UUID
    data: dict


@router.post("/quick-import")
async def quick_import(payload: QuickImportPayload, db: AsyncSession = Depends(get_db)):
    """Import data from a ChatGPT-generated JSON into an existing persona.

    Adds memories, writing samples, and policies to the persona.
    Optionally updates persona core fields (identity, values, tone, etc.).
    """
    persona = await db.get(PersonaCore, payload.persona_id)
    if not persona:
        return ORJSONResponse({"error": "Persona not found"}, status_code=404)

    data = payload.data
    counts = {
        "memories": 0,
        "writing_samples": 0,
        "policies": 0,
        "persona_updated": False,
    }

    # ── Update persona core fields if provided ──
    persona_data = data.get("persona")
    if persona_data and isinstance(persona_data, dict):
        updatable = QuickImportPersonaUpdate(
            **{
                k: v
                for k, v in persona_data.items()
                if k in QuickImportPersonaUpdate.model_fields and v is not None
            }
        )
        for field, value in updatable.model_dump(exclude_none=True).items():
            setattr(persona, field, value)
        counts["persona_updated"] = True

    # ── Import memories ──
    for mem_data in data.get("memories", []):
        try:
            validated = QuickImportMemory(**mem_data)
        except Exception:
            continue
        mem = Memory(
            persona_id=payload.persona_id,
            memory_type=validated.memory_type,
            title=validated.title,
            content=validated.content,
            source="quick_import",
            confidence=1.0,
            tags=validated.tags,
        )
        db.add(mem)
        counts["memories"] += 1

    # ── Import writing samples ──
    for ws_data in data.get("writing_samples", []):
        try:
            validated = QuickImportWritingSample(**ws_data)
        except Exception:
            continue
        ws = WritingSample(
            persona_id=payload.persona_id,
            content=validated.content,
            context_type=validated.context_type,
            tone=validated.tone,
            is_representative=True,
        )
        db.add(ws)
        counts["writing_samples"] += 1

    # ── Import policies ──
    for pol_data in data.get("policies", []):
        try:
            validated = QuickImportPolicy(**pol_data)
        except Exception:
            continue
        pol = PolicyRule(
            persona_id=payload.persona_id,
            policy_type=validated.policy_type,
            name=validated.name,
            description=validated.description,
        )
        db.add(pol)
        counts["policies"] += 1

    await db.flush()

    return {
        "status": "ok",
        "persona_id": str(payload.persona_id),
        "imported": counts,
    }
