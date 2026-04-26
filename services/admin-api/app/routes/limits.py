from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_session
from app.models import User, UserLimit
from app.schemas import UserLimitResponse, UserLimitUpdate

router = APIRouter(prefix="/users", tags=["limits"])


@router.get("/{user_id}/limits", response_model=UserLimitResponse)
async def get_limits(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    limit = await session.get(UserLimit, user_id)
    if limit is None:
        raise HTTPException(404, "Limits not found for this user")
    return limit


@router.put("/{user_id}/limits", response_model=UserLimitResponse)
async def update_limits(
    user_id: int,
    data: UserLimitUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    limit = await session.get(UserLimit, user_id)
    if limit is None:
        limit = UserLimit(
            user_id=user_id,
            daily_limit=data.daily_limit or 100000,
            monthly_limit=data.monthly_limit or 500000,
        )
        session.add(limit)
    else:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(limit, field, value)
        # onupdate= не работает через setattr — выставляем явно
        limit.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(limit)
    return limit
