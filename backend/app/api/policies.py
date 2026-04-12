"""Policy rule routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.policy import PolicyRule
from app.schemas.core import PolicyRuleCreate, PolicyRuleRead, PolicyRuleUpdate

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post("/", response_model=PolicyRuleRead, status_code=201)
async def create_policy(data: PolicyRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = PolicyRule(**data.model_dump(exclude_none=True))
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.get("/", response_model=list[PolicyRuleRead])
async def list_policies(
    response: Response,
    persona_id: UUID = Query(...),
    policy_type: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    count_stmt = select(func.count(PolicyRule.id)).where(
        PolicyRule.persona_id == persona_id
    )
    if policy_type:
        count_stmt = count_stmt.where(PolicyRule.policy_type == policy_type)
    total = (await db.execute(count_stmt)).scalar() or 0
    response.headers["X-Total-Count"] = str(total)

    stmt = (
        select(PolicyRule)
        .where(PolicyRule.persona_id == persona_id)
        .order_by(PolicyRule.priority.desc(), PolicyRule.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if policy_type:
        stmt = stmt.where(PolicyRule.policy_type == policy_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/{rule_id}", response_model=PolicyRuleRead)
async def update_policy(
    rule_id: UUID, data: PolicyRuleUpdate, db: AsyncSession = Depends(get_db)
):
    rule = await db.get(PolicyRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Policy not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.version += 1
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(PolicyRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(rule)
    await db.flush()
