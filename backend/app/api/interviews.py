"""Interview routes — sessions and answers."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import ensure_persona_access
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.interview import InterviewAnswer, InterviewSession
from app.models.user import User
from app.schemas.core import (
    InterviewAnswerCreate,
    InterviewAnswerRead,
    InterviewAnswerUpdate,
    InterviewSessionCreate,
    InterviewSessionRead,
)

router = APIRouter(prefix="/interviews", tags=["Interview"])


async def _session_persona_id(db: AsyncSession, session_id: UUID) -> UUID | None:
    session = await db.get(InterviewSession, session_id)
    return session.persona_id if session else None


@router.post("/sessions", response_model=InterviewSessionRead, status_code=201)
async def create_session(
    data: InterviewSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await ensure_persona_access(data.persona_id, user, db)
    session = InterviewSession(**data.model_dump())
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[InterviewSessionRead])
async def list_sessions(
    response: Response,
    persona_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await ensure_persona_access(persona_id, user, db)
    base = select(InterviewSession).where(InterviewSession.persona_id == persona_id)
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    stmt = base.order_by(InterviewSession.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    response.headers["X-Total-Count"] = str(total)
    return list(result.scalars().all())


@router.get("/sessions/{session_id}", response_model=InterviewSessionRead)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await ensure_persona_access(session.persona_id, user, db)
    return session


@router.post("/answers", response_model=InterviewAnswerRead, status_code=201)
async def create_answer(
    data: InterviewAnswerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await db.get(InterviewSession, data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await ensure_persona_access(session.persona_id, user, db)
    answer = InterviewAnswer(**data.model_dump())
    db.add(answer)
    session.question_count += 1
    await db.flush()
    await db.refresh(answer)
    return answer


@router.patch("/answers/{answer_id}", response_model=InterviewAnswerRead)
async def update_answer(
    answer_id: UUID,
    data: InterviewAnswerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    answer = await db.get(InterviewAnswer, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    persona_id = await _session_persona_id(db, answer.session_id)
    if persona_id:
        await ensure_persona_access(persona_id, user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(answer, field, value)
    await db.flush()
    await db.refresh(answer)
    return answer
