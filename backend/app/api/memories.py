"""Memory CRUD API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import ensure_persona_access
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.persona import MemoryCreate, MemoryRead, MemoryUpdate
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["Memories"])


def _svc(db: AsyncSession = Depends(get_db)) -> MemoryService:
    return MemoryService(db)


@router.post("/", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(
    data: MemoryCreate,
    svc: MemoryService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_persona_access(data.persona_id, user, db)
    return await svc.create(data)


@router.get("/", response_model=list[MemoryRead])
async def list_memories(
    response: Response,
    persona_id: UUID = Query(...),
    memory_type: str | None = None,
    approval_status: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    svc: MemoryService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_persona_access(persona_id, user, db)
    total = await svc.count_by_persona(
        persona_id, memory_type=memory_type, approval_status=approval_status
    )
    response.headers["X-Total-Count"] = str(total)
    return await svc.list_by_persona(
        persona_id,
        memory_type=memory_type,
        approval_status=approval_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{memory_id}", response_model=MemoryRead)
async def get_memory(
    memory_id: UUID,
    svc: MemoryService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    memory = await svc.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    await ensure_persona_access(memory.persona_id, user, db)
    return memory


@router.patch("/{memory_id}", response_model=MemoryRead)
async def update_memory(
    memory_id: UUID,
    data: MemoryUpdate,
    svc: MemoryService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    memory = await svc.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    await ensure_persona_access(memory.persona_id, user, db)
    updated = await svc.update(memory_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Memory not found")
    return updated


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    svc: MemoryService = Depends(_svc),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    memory = await svc.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    await ensure_persona_access(memory.persona_id, user, db)
    if not await svc.delete(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
