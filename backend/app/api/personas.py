"""Persona CRUD API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import get_owned_persona
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.persona import PersonaCore
from app.models.user import User
from app.schemas.persona import (
    PersonaCoreCreate,
    PersonaCoreRead,
    PersonaCoreUpdate,
)
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/personas", tags=["Persona Core"])


def _svc(db: AsyncSession = Depends(get_db)) -> PersonaService:
    return PersonaService(db)


@router.post("/", response_model=PersonaCoreRead, status_code=status.HTTP_201_CREATED)
async def create_persona(
    data: PersonaCoreCreate,
    svc: PersonaService = Depends(_svc),
    user: User = Depends(get_current_user),
):
    return await svc.create(data, owner_id=user.id)


@router.get("/", response_model=list[PersonaCoreRead])
async def list_personas(
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: PersonaService = Depends(_svc),
    user: User = Depends(get_current_user),
):
    if user.is_admin:
        items, total = await svc.list_all(limit=limit, offset=offset)
    else:
        items, total = await svc.list_for_owner(user.id, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/{persona_id}", response_model=PersonaCoreRead)
async def get_persona(persona: PersonaCore = Depends(get_owned_persona)):
    return persona


@router.patch("/{persona_id}", response_model=PersonaCoreRead)
async def update_persona(
    persona_id: UUID,
    data: PersonaCoreUpdate,
    svc: PersonaService = Depends(_svc),
    persona: PersonaCore = Depends(get_owned_persona),
):
    updated = await svc.update(persona_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Persona not found")
    return updated


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: UUID,
    svc: PersonaService = Depends(_svc),
    persona: PersonaCore = Depends(get_owned_persona),
):
    if not await svc.delete(persona_id):
        raise HTTPException(status_code=404, detail="Persona not found")
