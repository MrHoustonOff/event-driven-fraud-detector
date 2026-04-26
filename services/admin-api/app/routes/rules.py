from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_session
from app.models import FraudRule, User
from app.schemas import FraudRuleCreate, FraudRuleResponse, FraudRuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[FraudRuleResponse])
async def list_rules(
    is_active: bool | None = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(FraudRule)
    if is_active is not None:
        q = q.where(FraudRule.is_active == is_active)
    return (await session.scalars(q)).all()


@router.post("", response_model=FraudRuleResponse, status_code=201)
async def create_rule(
    data: FraudRuleCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    if await session.scalar(select(FraudRule).where(FraudRule.name == data.name)):
        raise HTTPException(400, "Rule name already exists")
    rule = FraudRule(**data.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=FraudRuleResponse)
async def update_rule(
    rule_id: int,
    data: FraudRuleUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    rule = await session.get(FraudRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    rule = await session.get(FraudRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    await session.delete(rule)
    await session.commit()
