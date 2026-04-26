import json
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.kafka.producer import producer_manager
from app.models import Transaction
from app.rules import (
    FraudEngine,
    HighFrequencyRule,
    LargeAmountRule,
    NewCountryRule,
    NightTimeRule,
    TransactionContext,
    UnusualCityRule,
    VelocityAmountRule,
)
from shared.schemas import AlertEvent, TransactionEvent, TransactionStatus

logger = logging.getLogger(__name__)

_engine = FraudEngine(
    [
        LargeAmountRule(),
        NewCountryRule(),
        HighFrequencyRule(),
        NightTimeRule(),
        UnusualCityRule(),
        VelocityAmountRule(),
    ]
)


def _to_event(tx: Transaction) -> TransactionEvent:
    return TransactionEvent(
        transaction_id=tx.id,
        user_id=tx.user_id,
        amount=tx.amount,
        currency=tx.currency,
        country=tx.country,
        city=tx.city,
        merchant=tx.merchant,
        created_at=tx.created_at,
    )


async def handle_message(event: TransactionEvent, session: AsyncSession) -> None:
    tx = await session.scalar(
        select(Transaction).where(Transaction.id == event.transaction_id)
    )
    if tx is None:
        logger.warning("transaction %s not found, skipping", event.transaction_id)
        return
    if tx.status != TransactionStatus.PENDING.value:
        logger.info(
            "transaction %s already processed (%s), skipping",
            event.transaction_id,
            tx.status,
        )
        return

    rows = await session.execute(
        select(Transaction)
        .where(
            Transaction.user_id == event.user_id, Transaction.id != event.transaction_id
        )
        .order_by(Transaction.created_at.desc())
        .limit(100)
    )
    history = [_to_event(t) for t in rows.scalars().all()]

    score, triggered = await _engine.evaluate(
        TransactionContext(tx=event, history=history)
    )

    if score >= 70:
        status = TransactionStatus.BLOCKED
    elif score >= 50:
        status = TransactionStatus.FLAGGED
    else:
        status = TransactionStatus.APPROVED

    await session.execute(
        update(Transaction)
        .where(Transaction.id == event.transaction_id)
        .values(status=status.value, fraud_score=score, updated_at=func.now())
    )
    await session.commit()

    if score >= 50:
        await producer_manager.publish(
            "alerts",
            AlertEvent(
                transaction_id=event.transaction_id,
                user_id=event.user_id,
                fraud_score=score,
                triggered_rules=triggered,
                created_at=datetime.now(timezone.utc),
            ),
        )


async def consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        "tx.raw",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="fraud-detector-group",
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
