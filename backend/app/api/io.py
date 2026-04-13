"""Import / Export routes — persona bundles, memories, graph snapshots."""

import json
from uuid import UUID

from agents import Runner
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.definitions import document_profile_extractor_agent
from app.core.deps import get_optional_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.ingestion.document_parser import (
    SUPPORTED_DOCUMENT_TYPES,
    UnsupportedDocumentTypeError,
    parse_document,
)
from app.ingestion.profile_merge import (
    build_existing_import_index,
    dedupe_memory_items,
    dedupe_policy_items,
    dedupe_writing_samples,
    estimate_import_counts,
    merge_document_payloads,
)
from app.models.agent_config import AgentConfig
from app.models.interview import InterviewAnswer, InterviewSession
from app.models.persona import Memory, PersonaCore, WritingSample
from app.models.policy import PolicyRule
from app.models.testing import TestScenario
from app.models.user import User
from app.services.provider_settings import resolve_provider_settings

router = APIRouter(prefix="/io", tags=["Import / Export"])
logger = get_logger("io")


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
    ask_before_acting: list[str] | None = None


class QuickImportPayload(BaseModel):
    persona_id: UUID
    data: dict
    source_label: str | None = None


class DocumentTrait(BaseModel):
    key: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class DocumentImportCounts(BaseModel):
    memories: int = 0
    writing_samples: int = 0
    policies: int = 0


class DocumentAnalysisResponse(BaseModel):
    filename: str
    document_type: str
    source_kind: str
    char_count: int
    used_char_count: int
    chunk_count: int
    analyzed_chunk_count: int
    was_truncated: bool
    preview_text: str
    summary: str = ""
    persona_would_change: bool = False
    estimated_new_counts: DocumentImportCounts = Field(
        default_factory=DocumentImportCounts
    )
    duplicate_counts: DocumentImportCounts = Field(default_factory=DocumentImportCounts)
    persona: QuickImportPersonaUpdate | None = None
    memories: list[QuickImportMemory] = Field(default_factory=list)
    writing_samples: list[QuickImportWritingSample] = Field(default_factory=list)
    policies: list[QuickImportPolicy] = Field(default_factory=list)
    traits: list[DocumentTrait] = Field(default_factory=list)


def _make_source_label(source_label: str | None) -> str:
    if not source_label:
        return "quick_import"
    cleaned = source_label.strip()
    if not cleaned:
        return "quick_import"
    if not cleaned.startswith("document:"):
        cleaned = f"document:{cleaned}"
    return cleaned[:255]


def _parse_persona_update(data: dict) -> QuickImportPersonaUpdate | None:
    persona_data = data.get("persona")
    if not persona_data or not isinstance(persona_data, dict):
        return None

    filtered = {
        key: value
        for key, value in persona_data.items()
        if key in QuickImportPersonaUpdate.model_fields and value is not None
    }
    if not filtered:
        return None
    return QuickImportPersonaUpdate(**filtered)


def _load_json_output(output: str) -> dict:
    cleaned = output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return json.loads(cleaned)


def _persona_would_change(
    persona: PersonaCore, persona_update: QuickImportPersonaUpdate | None
) -> bool:
    if not persona_update:
        return False
    for field, value in persona_update.model_dump(exclude_none=True).items():
        if getattr(persona, field) != value:
            return True
    return False


async def _apply_import_data(
    persona: PersonaCore,
    data: dict,
    db: AsyncSession,
    *,
    source_label: str | None = None,
) -> dict[str, int | bool]:
    counts = {
        "memories": 0,
        "writing_samples": 0,
        "policies": 0,
        "persona_updated": False,
        "duplicate_memories": 0,
        "duplicate_writing_samples": 0,
        "duplicate_policies": 0,
        "skipped_duplicates": 0,
    }

    persona_update = _parse_persona_update(data)
    if persona_update and _persona_would_change(persona, persona_update):
        for field, value in persona_update.model_dump(exclude_none=True).items():
            setattr(persona, field, value)
        counts["persona_updated"] = True

    import_source = _make_source_label(source_label)
    metadata_extra = {"source_label": source_label} if source_label else None
    existing_memories = (
        await db.execute(select(Memory).where(Memory.persona_id == persona.id))
    ).scalars().all()
    existing_writing_samples = (
        await db.execute(select(WritingSample).where(WritingSample.persona_id == persona.id))
    ).scalars().all()
    existing_policies = (
        await db.execute(select(PolicyRule).where(PolicyRule.persona_id == persona.id))
    ).scalars().all()

    existing_index = build_existing_import_index(
        list(existing_memories),
        list(existing_writing_samples),
        list(existing_policies),
    )

    deduped_memories, duplicate_memories = dedupe_memory_items(data.get("memories", []))
    deduped_samples, duplicate_samples = dedupe_writing_samples(
        data.get("writing_samples", [])
    )
    deduped_policies, duplicate_policies = dedupe_policy_items(data.get("policies", []))
    counts["duplicate_memories"] += duplicate_memories
    counts["duplicate_writing_samples"] += duplicate_samples
    counts["duplicate_policies"] += duplicate_policies

    memory_titles = set(existing_index["memory_titles"])
    memory_contents = set(existing_index["memory_contents"])
    sample_contents = set(existing_index["sample_contents"])
    policy_names = set(existing_index["policy_names"])
    policy_descriptions = set(existing_index["policy_descriptions"])

    for mem_data in deduped_memories:
        try:
            validated = QuickImportMemory(**mem_data)
        except Exception:
            continue
        memory_title_key = (
            validated.memory_type,
            " ".join(validated.title.lower().split()),
        )
        memory_content_key = " ".join(validated.content.lower().split())
        if (memory_title_key[1] and memory_title_key in memory_titles) or (
            memory_content_key and memory_content_key in memory_contents
        ):
            counts["duplicate_memories"] += 1
            continue
        mem = Memory(
            persona_id=persona.id,
            memory_type=validated.memory_type,
            title=validated.title,
            content=validated.content,
            source=import_source,
            confidence=1.0,
            tags=validated.tags,
            metadata_extra=metadata_extra,
        )
        db.add(mem)
        counts["memories"] += 1
        if memory_title_key[1]:
            memory_titles.add(memory_title_key)
        if memory_content_key:
            memory_contents.add(memory_content_key)

    for ws_data in deduped_samples:
        try:
            validated = QuickImportWritingSample(**ws_data)
        except Exception:
            continue
        sample_content_key = " ".join(validated.content.lower().split())
        if sample_content_key in sample_contents:
            counts["duplicate_writing_samples"] += 1
            continue
        ws = WritingSample(
            persona_id=persona.id,
            content=validated.content,
            context_type=validated.context_type,
            tone=validated.tone,
            is_representative=True,
            metadata_extra=metadata_extra,
        )
        db.add(ws)
        counts["writing_samples"] += 1
        sample_contents.add(sample_content_key)

    for pol_data in deduped_policies:
        try:
            validated = QuickImportPolicy(**pol_data)
        except Exception:
            continue
        policy_name_key = (
            validated.policy_type,
            " ".join(validated.name.lower().split()),
        )
        policy_description_key = " ".join(validated.description.lower().split())
        if (policy_name_key[1] and policy_name_key in policy_names) or (
            policy_description_key and policy_description_key in policy_descriptions
        ):
            counts["duplicate_policies"] += 1
            continue
        pol = PolicyRule(
            persona_id=persona.id,
            policy_type=validated.policy_type,
            name=validated.name,
            description=validated.description,
        )
        db.add(pol)
        counts["policies"] += 1
        if policy_name_key[1]:
            policy_names.add(policy_name_key)
        if policy_description_key:
            policy_descriptions.add(policy_description_key)

    counts["skipped_duplicates"] = (
        counts["duplicate_memories"]
        + counts["duplicate_writing_samples"]
        + counts["duplicate_policies"]
    )
    await db.flush()
    return counts


@router.post("/analyze-document", response_model=DocumentAnalysisResponse)
async def analyze_document(
    persona_id: UUID = Form(...),
    source_kind: str = Form("general"),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Analyze a document and convert it into persona training data."""
    provider_settings = resolve_provider_settings(user)
    if not provider_settings.configured:
        raise HTTPException(400, "Provider API key not configured")

    persona = await db.get(PersonaCore, persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")

    filename = file.filename or "document"
    try:
        parsed_document = parse_document(filename, await file.read())
    except UnsupportedDocumentTypeError as exc:
        supported = ", ".join(sorted(ext.lstrip(".") for ext in SUPPORTED_DOCUMENT_TYPES))
        raise HTTPException(400, f"{exc}. Supported types: {supported}") from exc
    except Exception as exc:
        logger.error("document_parse_failed", filename=filename, error=str(exc))
        raise HTTPException(400, "Failed to parse document") from exc

    if not parsed_document.text:
        raise HTTPException(400, "Document did not contain any readable text")
    if not parsed_document.analysis_chunks:
        raise HTTPException(400, "Document did not contain any analyzable text")

    existing_memories = (
        await db.execute(select(Memory).where(Memory.persona_id == persona_id))
    ).scalars().all()
    existing_policies = (
        await db.execute(select(PolicyRule).where(PolicyRule.persona_id == persona_id))
    ).scalars().all()
    existing_samples = (
        await db.execute(select(WritingSample).where(WritingSample.persona_id == persona_id))
    ).scalars().all()

    memory_titles_preview = "\n".join(
        memory.title for memory in list(existing_memories)[:50]
    ) or "None"
    policy_names_preview = "\n".join(
        policy.name for policy in list(existing_policies)[:50]
    ) or "None"
    sample_contexts_preview = "\n".join(
        sample.context_type for sample in list(existing_samples)[:50]
    ) or "None"

    chunk_payloads: list[dict] = []
    for chunk in parsed_document.analysis_chunks:
        prompt = f"""TARGET PERSONA
Name: {persona.name}
Identity summary: {persona.identity_summary or "Not defined yet"}

DOCUMENT METADATA
Filename: {parsed_document.filename}
Detected type: {parsed_document.document_type}
Declared source kind: {source_kind}
Operator notes: {notes or "None"}
Chunk: {chunk.index} of {chunk.total}

EXISTING MEMORY TITLES (avoid duplicates)
{memory_titles_preview}

EXISTING POLICY NAMES (avoid duplicates)
{policy_names_preview}

EXISTING WRITING SAMPLE CONTEXTS
{sample_contexts_preview}

DOCUMENT TEXT
{chunk.text}
"""
        result = await Runner.run(
            document_profile_extractor_agent,
            input=prompt,
            run_config=provider_settings.to_run_config(),
        )

        try:
            chunk_payloads.append(_load_json_output(result.final_output))
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error(
                "document_analysis_parse_failed",
                filename=filename,
                chunk_index=chunk.index,
                output=result.final_output,
            )
            raise HTTPException(500, "Failed to analyze document") from exc

    merged_data = merge_document_payloads(chunk_payloads)
    persona_update = _parse_persona_update(merged_data)
    existing_index = build_existing_import_index(
        list(existing_memories),
        list(existing_samples),
        list(existing_policies),
    )
    estimated_new_counts, duplicate_counts = estimate_import_counts(
        merged_data, existing_index
    )
    memories: list[QuickImportMemory] = []
    writing_samples: list[QuickImportWritingSample] = []
    policies: list[QuickImportPolicy] = []
    traits: list[DocumentTrait] = []

    for item in merged_data.get("memories", []):
        try:
            memories.append(QuickImportMemory(**item))
        except Exception:
            continue

    for item in merged_data.get("writing_samples", []):
        try:
            writing_samples.append(QuickImportWritingSample(**item))
        except Exception:
            continue

    for item in merged_data.get("policies", []):
        try:
            policies.append(QuickImportPolicy(**item))
        except Exception:
            continue

    for item in merged_data.get("traits", []):
        try:
            traits.append(DocumentTrait(**item))
        except Exception:
            continue

    analysis = DocumentAnalysisResponse(
        filename=parsed_document.filename,
        document_type=parsed_document.document_type,
        source_kind=source_kind,
        char_count=parsed_document.char_count,
        used_char_count=parsed_document.used_char_count,
        chunk_count=parsed_document.total_chunk_count,
        analyzed_chunk_count=parsed_document.analyzed_chunk_count,
        was_truncated=parsed_document.was_truncated,
        preview_text=parsed_document.text[:1200],
        summary=merged_data.get("summary", ""),
        persona_would_change=_persona_would_change(persona, persona_update),
        estimated_new_counts=DocumentImportCounts(**estimated_new_counts),
        duplicate_counts=DocumentImportCounts(**duplicate_counts),
        persona=persona_update,
        memories=memories,
        writing_samples=writing_samples,
        policies=policies,
        traits=traits,
    )
    return analysis


@router.post("/quick-import")
async def quick_import(payload: QuickImportPayload, db: AsyncSession = Depends(get_db)):
    """Import data from a ChatGPT-generated JSON into an existing persona.

    Adds memories, writing samples, and policies to the persona.
    Optionally updates persona core fields (identity, values, tone, etc.).
    """
    persona = await db.get(PersonaCore, payload.persona_id)
    if not persona:
        return ORJSONResponse({"error": "Persona not found"}, status_code=404)
    counts = await _apply_import_data(
        persona,
        payload.data,
        db,
        source_label=payload.source_label,
    )

    return {
        "status": "ok",
        "persona_id": str(payload.persona_id),
        "imported": counts,
    }
