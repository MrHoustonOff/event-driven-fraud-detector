import json
import logging

import httpx
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models import Notification
from shared.schemas import AlertEvent, LimitExceededEvent

logger = logging.getLogger(__name__)


async def handle_message(
    event: AlertEvent | LimitExceededEvent,
    notification_type: str,
    session: AsyncSession,
    http_client: httpx.AsyncClient,
) -> None:
    payload = json.loads(event.model_dump_json())

    status = "sent"
    error_message = None

    try:
        resp = await http_client.post(settings.webhook_url, json=payload, timeout=5.0)
        if resp.status_code >= 300:
            status = "failed"
            error_message = f"HTTP {resp.status_code}"
    except Exception as e:
        status = "failed"
        error_message = str(e)[:500]

    session.add(Notification(
        user_id=event.user_id,
        notification_type=notification_type,
        payload=payload,
        status=status,
        error_message=error_message,
    ))
    await session.commit()

    logger.info("notification %s for user %s: %s", notification_type, event.user_id, status)


async def consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        "alerts", "limit_exceeded",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="notify-service-group",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    await consumer.start()
    try:
        async with httpx.AsyncClient() as http_client:
            async for msg in consumer:
                async with AsyncSessionLocal() as session:
                    try:
                        if msg.topic == "alerts":
                            event = AlertEvent.model_validate(msg.value)
                            notification_type = "fraud_alert"
                        else:
                            event = LimitExceededEvent.model_validate(msg.value)
                            notification_type = "limit_exceeded"

                        await handle_message(event, notification_type, session, http_client)
                        await consumer.commit()
                    except Exception:
                        logger.exception("failed to process message: %s", msg.value)
    finally:
        await consumer.stop()
