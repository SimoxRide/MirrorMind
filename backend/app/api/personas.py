"""Persona CRUD API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
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
async def create_persona(data: PersonaCoreCreate, svc: PersonaService = Depends(_svc)):
    return await svc.create(data)


@router.get("/", response_model=list[PersonaCoreRead])
async def list_personas(svc: PersonaService = Depends(_svc)):
    return await svc.list_all()


@router.get("/{persona_id}", response_model=PersonaCoreRead)
async def get_persona(persona_id: UUID, svc: PersonaService = Depends(_svc)):
    persona = await svc.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.patch("/{persona_id}", response_model=PersonaCoreRead)
async def update_persona(
    persona_id: UUID, data: PersonaCoreUpdate, svc: PersonaService = Depends(_svc)
):
    persona = await svc.update(persona_id, data)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(persona_id: UUID, svc: PersonaService = Depends(_svc)):
    if not await svc.delete(persona_id):
        raise HTTPException(status_code=404, detail="Persona not found")
