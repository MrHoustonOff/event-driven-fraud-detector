from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.kafka.consumer import DEFAULT_DAILY_LIMIT, DEFAULT_MONTHLY_LIMIT
from app.models import SpendingLog, UserLimit
from app.schemas import LimitsResponse, LimitsUpdate

router = APIRouter()


def _time_ranges() -> tuple[datetime, datetime, datetime, datetime]:
    now_utc = datetime.now(timezone.utc)
    day_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)
    return day_start, day_start + timedelta(days=1), month_start, next_month_start


async def _get_spent(user_id: int, session: AsyncSession) -> tuple[Decimal, Decimal]:
    day_start, day_end, month_start, next_month_start = _time_ranges()

    daily_result = await session.execute(
        select(func.sum(SpendingLog.amount)).where(
            SpendingLog.user_id == user_id,
            SpendingLog.created_at >= day_start,
            SpendingLog.created_at < day_end,
        )
    )
    monthly_result = await session.execute(
        select(func.sum(SpendingLog.amount)).where(
            SpendingLog.user_id == user_id,
            SpendingLog.created_at >= month_start,
            SpendingLog.created_at < next_month_start,
        )
    )
    return (
        daily_result.scalar() or Decimal("0.00"),
        monthly_result.scalar() or Decimal("0.00"),
    )


@router.get("/limits/{user_id}", response_model=LimitsResponse)
async def get_limits(user_id: int, session: AsyncSession = Depends(get_session)):
    limits = await session.scalar(
        select(UserLimit).where(UserLimit.user_id == user_id)
    )
    daily_limit = limits.daily_limit if limits else DEFAULT_DAILY_LIMIT
    monthly_limit = limits.monthly_limit if limits else DEFAULT_MONTHLY_LIMIT

    spent_today, spent_this_month = await _get_spent(user_id, session)

    return LimitsResponse(
        user_id=user_id,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
        spent_today=spent_today,
        spent_this_month=spent_this_month,
    )


@router.put("/limits/{user_id}", response_model=LimitsResponse)
async def update_limits(
    user_id: int,
    body: LimitsUpdate,
    session: AsyncSession = Depends(get_session),
):
    limits = await session.scalar(
        select(UserLimit).where(UserLimit.user_id == user_id)
    )
    if limits is None:
        limits = UserLimit(
            user_id=user_id,
            daily_limit=DEFAULT_DAILY_LIMIT,
            monthly_limit=DEFAULT_MONTHLY_LIMIT,
        )
        session.add(limits)
        await session.flush()

    values: dict = {"updated_at": func.now()}
    if body.daily_limit is not None:
        values["daily_limit"] = body.daily_limit
    if body.monthly_limit is not None:
        values["monthly_limit"] = body.monthly_limit

    await session.execute(
        update(UserLimit).where(UserLimit.user_id == user_id).values(**values)
    )
    await session.commit()

    updated = await session.scalar(
        select(UserLimit).where(UserLimit.user_id == user_id)
    )
    spent_today, spent_this_month = await _get_spent(user_id, session)

    return LimitsResponse(
        user_id=user_id,
        daily_limit=updated.daily_limit,
        monthly_limit=updated.monthly_limit,
        spent_today=spent_today,
        spent_this_month=spent_this_month,
    )
