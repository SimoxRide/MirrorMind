"""Writing sample routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.persona import (
    WritingSampleCreate,
    WritingSampleRead,
    WritingSampleUpdate,
)
from app.services.writing_sample_service import WritingSampleService

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
