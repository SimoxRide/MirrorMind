"""Interview routes — sessions and answers."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.interview import InterviewAnswer, InterviewSession
from app.schemas.core import (
    InterviewAnswerCreate,
    InterviewAnswerRead,
    InterviewAnswerUpdate,
    InterviewSessionCreate,
    InterviewSessionRead,
)

router = APIRouter(prefix="/interviews", tags=["Interview"])


@router.post("/sessions", response_model=InterviewSessionRead, status_code=201)
async def create_session(
    data: InterviewSessionCreate, db: AsyncSession = Depends(get_db)
):
    session = InterviewSession(**data.model_dump())
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[InterviewSessionRead])
async def list_sessions(
    persona_id: UUID = Query(...), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(InterviewSession)
        .where(InterviewSession.persona_id == persona_id)
        .order_by(InterviewSession.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/sessions/{session_id}", response_model=InterviewSessionRead)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/answers", response_model=InterviewAnswerRead, status_code=201)
async def create_answer(
    data: InterviewAnswerCreate, db: AsyncSession = Depends(get_db)
):
    answer = InterviewAnswer(**data.model_dump())
    db.add(answer)
    # update session question count
    session = await db.get(InterviewSession, data.session_id)
    if session:
        session.question_count += 1
    await db.flush()
    await db.refresh(answer)
    return answer


@router.patch("/answers/{answer_id}", response_model=InterviewAnswerRead)
async def update_answer(
    answer_id: UUID, data: InterviewAnswerUpdate, db: AsyncSession = Depends(get_db)
):
    answer = await db.get(InterviewAnswer, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(answer, field, value)
    await db.flush()
    await db.refresh(answer)
    return answer
