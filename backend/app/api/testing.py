"""Testing lab & evaluation routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_optional_current_user
from app.db.session import get_db
from app.models.testing import Evaluation, TestResult, TestScenario
from app.models.user import User
from app.schemas.core import (
    CloneRequest,
    CloneResponse,
    EvaluationCreate,
    EvaluationRead,
    TestScenarioCreate,
    TestScenarioRead,
)

router = APIRouter(prefix="/testing", tags=["Testing Lab"])

SCENARIO_LOAD = selectinload(TestScenario.results).selectinload(TestResult.evaluations)


# ── Scenarios ────────────────────────────────────────────


@router.post("/scenarios", response_model=TestScenarioRead, status_code=201)
async def create_scenario(data: TestScenarioCreate, db: AsyncSession = Depends(get_db)):
    scenario = TestScenario(**data.model_dump(exclude_none=True))
    db.add(scenario)
    await db.flush()
    await db.refresh(scenario)
    return scenario


@router.get("/scenarios", response_model=list[TestScenarioRead])
async def list_scenarios(
    persona_id: UUID = Query(...),
    context_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TestScenario)
        .options(SCENARIO_LOAD)
        .where(TestScenario.persona_id == persona_id)
        .order_by(TestScenario.created_at.desc())
    )
    if context_type:
        stmt = stmt.where(TestScenario.context_type == context_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/scenarios/{scenario_id}", response_model=TestScenarioRead)
async def get_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(TestScenario).options(SCENARIO_LOAD).where(TestScenario.id == scenario_id)
    result = await db.execute(stmt)
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


# ── Run clone ────────────────────────────────────────────


@router.post("/run", response_model=CloneResponse)
async def run_clone(
    req: CloneRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Execute the clone pipeline for a single message.

    This route orchestrates the full clone generation flow:
    classify → retrieve → generate → critique → respond.
    """
    # Import here to avoid circular imports during startup
    from app.services.clone_engine import CloneEngine

    engine = CloneEngine(db)
    return await engine.generate(req, user=user)


# ── Evaluations ──────────────────────────────────────────


@router.post("/evaluations", response_model=EvaluationRead, status_code=201)
async def create_evaluation(data: EvaluationCreate, db: AsyncSession = Depends(get_db)):
    evaluation = Evaluation(**data.model_dump(exclude_none=True))
    db.add(evaluation)
    await db.flush()
    await db.refresh(evaluation)
    return evaluation


@router.get("/evaluations", response_model=list[EvaluationRead])
async def list_evaluations(
    test_result_id: UUID = Query(...), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Evaluation)
        .where(Evaluation.test_result_id == test_result_id)
        .order_by(Evaluation.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
