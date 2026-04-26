from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.schemas import TransactionEvent


def make_event(**kwargs) -> TransactionEvent:
    defaults = dict(
        transaction_id=uuid4(),
        user_id=1,
        amount=Decimal("500.00"),
        currency="RUB",
        country="RU",
        city="Moscow",
        merchant="Test",
        created_at=datetime.now(timezone.utc),
    )
    return TransactionEvent(**{**defaults, **kwargs})


@pytest.fixture
def pending_tx():
    tx = MagicMock()
    tx.status = "PENDING"
    tx.user_id = 1
    tx.id = uuid4()
    tx.amount = Decimal("500.00")
    tx.currency = "RUB"
    tx.country = "RU"
    tx.city = "Moscow"
    tx.merchant = "Test"
    tx.created_at = datetime.now(timezone.utc)
    return tx


@pytest.fixture
def session(pending_tx):
    s = AsyncMock(spec=AsyncSession)
    s.scalar.return_value = pending_tx
    mock_history = MagicMock()
    mock_history.scalars.return_value.all.return_value = []
    s.execute.side_effect = [mock_history, MagicMock()]  # SELECT history, then UPDATE
    return s


@pytest.fixture
def publish_mock():
    with patch("app.kafka.consumer.producer_manager.publish", new_callable=AsyncMock) as m:
        yield m
