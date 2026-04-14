"""Writing sample routes."""

import json
from uuid import UUID

from agents import Runner
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.definitions import style_analysis_agent
from app.core.deps import get_optional_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.persona import PersonaCore
from app.models.user import User
from app.schemas.persona import (
    WritingSampleCreate,
    WritingSampleRead,
    WritingSampleUpdate,
)
from app.services.provider_settings import resolve_provider_settings
from app.services.writing_sample_service import WritingSampleService

logger = get_logger("writing_samples")

router = APIRouter(prefix="/writing-samples", tags=["Writing Samples"])


def _svc(db: AsyncSession = Depends(get_db)) -> WritingSampleService:
    return WritingSampleService(db)


@router.post("/", response_model=WritingSampleRead, status_code=status.HTTP_201_CREATED)
async def create_sample(
    data: WritingSampleCreate, svc: WritingSampleService = Depends(_svc)
):
    return await svc.create(data)


@router.get("/", response_model=list[WritingSampleRead])
async def list_samples(
    response: Response,
    persona_id: UUID = Query(...),
    context_type: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    svc: WritingSampleService = Depends(_svc),
):
    total = await svc.count_by_persona(persona_id, context_type=context_type)
    response.headers["X-Total-Count"] = str(total)
    return await svc.list_by_persona(
        persona_id, context_type=context_type, limit=limit, offset=offset
    )


@router.get("/{sample_id}", response_model=WritingSampleRead)
async def get_sample(sample_id: UUID, svc: WritingSampleService = Depends(_svc)):
    sample = await svc.get(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Writing sample not found")
    return sample


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(sample_id: UUID, svc: WritingSampleService = Depends(_svc)):
    if not await svc.delete(sample_id):
        raise HTTPException(status_code=404, detail="Writing sample not found")


@router.patch("/{sample_id}", response_model=WritingSampleRead)
async def update_sample(
    sample_id: UUID,
    data: WritingSampleUpdate,
    svc: WritingSampleService = Depends(_svc),
):
    sample = await svc.update(sample_id, data.model_dump(exclude_unset=True))
    if not sample:
        raise HTTPException(status_code=404, detail="Writing sample not found")
    return sample


# ── Style Analysis ───────────────────────────────────────


class StyleProfileResponse(BaseModel):
    style_profile: dict
    samples_analyzed: int


@router.post("/analyze-style", response_model=StyleProfileResponse)
async def analyze_writing_style(
    persona_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Run the StyleAnalyzer agent on all writing samples and save
    an aggregated style profile (grammar, punctuation, emoji, etc.)
    to the persona."""
    provider_settings = resolve_provider_settings(user)
    if not provider_settings.configured:
        raise HTTPException(
            status_code=400,
            detail="An LLM provider API key is required for style analysis.",
        )

    persona = await db.get(PersonaCore, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found.")

    svc = WritingSampleService(db)
    samples = await svc.list_by_persona(persona_id, limit=50)
    if not samples:
        raise HTTPException(
            status_code=400,
            detail="No writing samples found. Add some samples first.",
        )

    # Assemble samples for the agent
    sample_texts = []
    for s in samples:
        header = f"[{s.context_type}]"
        if s.tone:
            header += f" tone={s.tone}"
        sample_texts.append(f"{header}\n{s.content}")

    prompt = (
        f"Analyze the following {len(samples)} writing samples from the person '{persona.name}'.\n"
        "Pay special attention to:\n"
        "- Grammar habits (correct vs informal, missing punctuation, run-on sentences)\n"
        "- Punctuation patterns (do they use periods? exclamation marks? ellipsis? commas?)\n"
        "- Capitalization habits (all lowercase? proper case? random caps?)\n"
        "- Typo patterns or deliberate misspellings\n"
        "- Language mixing (e.g., Italian with English words)\n"
        "- Sentence structure (short fragments vs long sentences)\n"
        "- Message structure (single block vs multiple short messages)\n\n"
        "=== WRITING SAMPLES ===\n\n" + "\n\n---\n\n".join(sample_texts)
    )

    result = await Runner.run(
        style_analysis_agent,
        input=prompt,
        run_config=provider_settings.to_run_config(),
    )

    try:
        style_profile = json.loads(result.final_output)
    except (json.JSONDecodeError, TypeError):
        style_profile = {"raw_analysis": result.final_output}

    # Save to persona
    persona.style_profile = style_profile
    await db.flush()
    await db.refresh(persona)

    logger.info(
        "style_analysis_complete",
        persona_id=str(persona_id),
        samples=len(samples),
    )

    return StyleProfileResponse(
        style_profile=style_profile,
        samples_analyzed=len(samples),
    )
