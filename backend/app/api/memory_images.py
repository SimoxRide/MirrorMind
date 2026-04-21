"""Memory image routes — upload, analyse and serve persona images.

Supports three ``kind`` values:

* ``self`` — a photo of the persona themselves; analysis seeds identity hints
  that can be merged back into ``PersonaCore.identity_summary``.
* ``person`` — a photo of someone in the persona's life.
* ``memory`` — a personal memory/scene photo, optionally linked to a Memory.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import ensure_persona_access
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.memory_image import MemoryImage
from app.models.persona import PersonaCore
from app.models.user import User
from app.schemas.memory_image import (
    MemoryImageAnalyzeResult,
    MemoryImageRead,
    MemoryImageUpdate,
)
from app.services.image_analysis import analyze_image
from app.services.memory_image_service import MemoryImageService

logger = get_logger("memory_images")

router = APIRouter(prefix="/memory-images", tags=["Memory Images"])

_ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
_ALLOWED_KINDS = {"self", "memory", "person"}


def _svc(db: AsyncSession = Depends(get_db)) -> MemoryImageService:
    return MemoryImageService(db)


async def _read_and_validate(file: UploadFile) -> tuple[bytes, str]:
    max_bytes = get_settings().max_document_bytes
    content_type = (file.content_type or "").lower() or "image/jpeg"
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {content_type}",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if max_bytes and len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(f"Image too large ({len(data)} > {max_bytes} bytes)."),
        )
    return data, content_type


async def _apply_self_analysis(
    persona: PersonaCore, analysis_payload: dict, db: AsyncSession
) -> bool:
    """Merge a 'self' analysis result into the persona. Returns True if updated."""
    if analysis_payload.get("status") != "ready":
        return False
    result = analysis_payload.get("result") or {}
    addendum = (result.get("identity_summary_addendum") or "").strip()
    if not addendum:
        return False
    current = (persona.identity_summary or "").strip()
    if addendum in current:
        return False
    persona.identity_summary = (
        f"{current}\n\n{addendum}".strip() if current else addendum
    )[:5000]
    await db.flush()
    return True


@router.post(
    "/",
    response_model=MemoryImageAnalyzeResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    request: Request,
    persona_id: UUID = Form(...),
    kind: str = Form("memory"),
    title: str = Form(""),
    caption: str | None = Form(None),
    memory_id: UUID | None = Form(None),
    tags: str | None = Form(None),
    analyze: bool = Form(True),
    file: UploadFile = File(...),
    svc: MemoryImageService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if kind not in _ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {kind}")
    persona = await ensure_persona_access(persona_id, user, db)

    data, content_type = await _read_and_validate(file)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    image = await svc.create(
        persona_id=persona_id,
        kind=kind,
        title=title or (file.filename or "image"),
        caption=caption,
        content_type=content_type,
        file_name=file.filename,
        data=data,
        memory_id=memory_id,
        tags=tag_list,
    )

    persona_updated = False
    if analyze:
        analysis_payload = await analyze_image(
            image_bytes=data,
            content_type=content_type,
            kind=kind,
            user=user,
            extra_context=caption,
        )
        image.analysis = analysis_payload
        image.analysis_status = analysis_payload.get("status", "failed")
        result = analysis_payload.get("result") or {}
        if not image.caption and isinstance(result.get("description"), str):
            image.caption = result["description"][:2000]
        if not tag_list and isinstance(result.get("suggested_tags"), list):
            image.tags = [str(t)[:64] for t in result["suggested_tags"][:12] if t]
        if kind == "self" and isinstance(persona, PersonaCore):
            persona_updated = await _apply_self_analysis(persona, analysis_payload, db)
        await db.flush()
        await db.refresh(image)

    return MemoryImageAnalyzeResult(
        image=MemoryImageRead.model_validate(image),
        persona_updated=persona_updated,
    )


@router.get("/", response_model=list[MemoryImageRead])
async def list_images(
    response: Response,
    persona_id: UUID = Query(...),
    kind: str | None = Query(None),
    memory_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
    svc: MemoryImageService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_persona_access(persona_id, user, db)
    total = await svc.count_by_persona(persona_id, kind=kind, memory_id=memory_id)
    response.headers["X-Total-Count"] = str(total)
    return await svc.list_by_persona(
        persona_id, kind=kind, memory_id=memory_id, limit=limit, offset=offset
    )


@router.get("/{image_id}", response_model=MemoryImageRead)
async def get_image(
    image_id: UUID,
    svc: MemoryImageService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    image = await svc.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    await ensure_persona_access(image.persona_id, user, db)
    return image


@router.get("/{image_id}/raw")
async def get_image_raw(
    image_id: UUID,
    svc: MemoryImageService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    image = await svc.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    await ensure_persona_access(image.persona_id, user, db)
    return Response(
        content=image.data,
        media_type=image.content_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.patch("/{image_id}", response_model=MemoryImageRead)
async def update_image(
    image_id: UUID,
    data: MemoryImageUpdate,
    svc: MemoryImageService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    image = await svc.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    await ensure_persona_access(image.persona_id, user, db)
    patch = data.model_dump(exclude_unset=True)
    updated = await svc.update(image_id, patch)
    return updated


@router.post("/{image_id}/analyze", response_model=MemoryImageAnalyzeResult)
async def reanalyze_image(
    image_id: UUID,
    apply_to_persona: bool = Query(False),
    svc: MemoryImageService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    image = await svc.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    persona = await ensure_persona_access(image.persona_id, user, db)

    analysis_payload = await analyze_image(
        image_bytes=image.data,
        content_type=image.content_type,
        kind=image.kind,
        user=user,
        extra_context=image.caption,
    )
    image.analysis = analysis_payload
    image.analysis_status = analysis_payload.get("status", "failed")

    persona_updated = False
    if image.kind == "self" and apply_to_persona and isinstance(persona, PersonaCore):
        persona_updated = await _apply_self_analysis(persona, analysis_payload, db)
    await db.flush()
    await db.refresh(image)

    return MemoryImageAnalyzeResult(
        image=MemoryImageRead.model_validate(image),
        persona_updated=persona_updated,
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: UUID,
    svc: MemoryImageService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    image = await svc.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    await ensure_persona_access(image.persona_id, user, db)
    await svc.delete(image_id)
