from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_session
from app.models import Notification, Transaction, User
from app.schemas import DashboardResponse, TopTransactionResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def dashboard(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    transactions_today = await session.scalar(
        select(func.count(Transaction.id)).where(Transaction.created_at >= today)
    ) or 0

    alerts_today = await session.scalar(
        select(func.count(Notification.id))
        .where(Notification.type == "fraud_alert")
        .where(Notification.created_at >= today)
    ) or 0

    blocked_today = await session.scalar(
        select(func.count(Transaction.id))
        .where(Transaction.status == "BLOCKED")
        .where(Transaction.created_at >= today)
    ) or 0

    top = (await session.scalars(
        select(Transaction)
        .where(Transaction.fraud_score.isnot(None))
        .order_by(Transaction.fraud_score.desc())
        .limit(5)
    )).all()

    return DashboardResponse(
        transactions_today=transactions_today,
        alerts_today=alerts_today,
        blocked_today=blocked_today,
        top_fraud_score=[TopTransactionResponse.model_validate(t) for t in top],
    )
