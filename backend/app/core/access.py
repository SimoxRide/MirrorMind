"""Access-control helpers: ownership checks for persona-scoped resources.

All persona-owned resources (memories, writing samples, policies, extensions,
production clones, interviews, agent configs, test scenarios) are scoped via
``PersonaCore.owner_id``. Admins bypass ownership checks.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.persona import PersonaCore
from app.models.user import User


async def get_owned_persona(
    persona_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PersonaCore:
    """Return a persona only if the caller owns it (or is admin).

    Raises 404 when missing, 403 when not owner.
    """
    persona = await db.get(PersonaCore, persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    if not user.is_admin and persona.owner_id not in (None, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this persona.",
        )
    return persona


async def ensure_persona_access(
    persona_id: UUID,
    user: User,
    db: AsyncSession,
) -> PersonaCore:
    """Functional variant usable inside route handlers (not as Depends)."""
    persona = await db.get(PersonaCore, persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    if not user.is_admin and persona.owner_id not in (None, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this persona.",
        )
    return persona


def can_access_persona(user: User, persona: PersonaCore) -> bool:
    if user.is_admin:
        return True
    return persona.owner_id in (None, user.id)
