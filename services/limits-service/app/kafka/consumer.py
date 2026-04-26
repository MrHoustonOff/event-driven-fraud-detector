import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aiokafka import AIOKafkaConsumer
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.kafka.producer import producer_manager
from app.models import SpendingLog, Transaction, UserLimit
from shared.schemas import LimitExceededEvent, TransactionEvent

logger = logging.getLogger(__name__)

DEFAULT_DAILY_LIMIT = Decimal("100000.00")
DEFAULT_MONTHLY_LIMIT = Decimal("500000.00")


async def handle_message(event: TransactionEvent, session: AsyncSession) -> None:
    # Idempotency level 1: skip if already processed
    existing = await session.scalar(
        select(SpendingLog).where(SpendingLog.transaction_id == event.transaction_id)
    )
    if existing:
        logger.info("transaction %s already in spending_log, skipping", event.transaction_id)
        return

    session.add(SpendingLog(
        user_id=event.user_id,
        amount=event.amount,
        transaction_id=event.transaction_id,
    ))

    try:
        await session.flush()
    except IntegrityError:
        # Idempotency level 2: race condition — another consumer inserted first
        await session.rollback()
        logger.info("transaction %s duplicate via UNIQUE constraint, skipping", event.transaction_id)
        return

    limits = await session.scalar(
        select(UserLimit).where(UserLimit.user_id == event.user_id)
    )
    daily_limit = limits.daily_limit if limits else DEFAULT_DAILY_LIMIT
    monthly_limit = limits.monthly_limit if limits else DEFAULT_MONTHLY_LIMIT

    now_utc = datetime.now(timezone.utc)
    day_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)

    daily_result = await session.execute(
        select(func.sum(SpendingLog.amount)).where(
            SpendingLog.user_id == event.user_id,
            SpendingLog.created_at >= day_start,
            SpendingLog.created_at < day_start + timedelta(days=1),
        )
    )
    daily_spent = daily_result.scalar() or Decimal("0.00")

    monthly_result = await session.execute(
        select(func.sum(SpendingLog.amount)).where(
            SpendingLog.user_id == event.user_id,
            SpendingLog.created_at >= month_start,
            SpendingLog.created_at < next_month_start,
        )
    )
    monthly_spent = monthly_result.scalar() or Decimal("0.00")

    limit_type: str | None = None
    current_spent: Decimal | None = None
    limit_value: Decimal | None = None

    if daily_spent > daily_limit:
        limit_type = "daily"
        current_spent = daily_spent
        limit_value = daily_limit
    elif monthly_spent > monthly_limit:
        limit_type = "monthly"
        current_spent = monthly_spent
        limit_value = monthly_limit

    if limit_type:
        await session.execute(
            update(Transaction)
            .where(Transaction.id == event.transaction_id)
            .values(status="BLOCKED", updated_at=func.now())
        )

    await session.commit()

    if limit_type:
        await producer_manager.publish(
            "limit_exceeded",
            LimitExceededEvent(
                transaction_id=event.transaction_id,
                user_id=event.user_id,
                limit_type=limit_type,
                current_spent=current_spent,
                limit_value=limit_value,
                created_at=datetime.now(timezone.utc),
            ),
        )
        logger.info(
            "limit exceeded for user %s: %s (%.2f > %.2f)",
            event.user_id, limit_type, current_spent, limit_value,
        )


async def consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        "tx.raw",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="limits-service-group",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            async with AsyncSessionLocal() as session:
                try:
                    event = TransactionEvent.model_validate(msg.value)
                    await handle_message(event, session)
                    await consumer.commit()
                except Exception:
                    logger.exception("failed to process message: %s", msg.value)
    finally:
        await consumer.stop()
