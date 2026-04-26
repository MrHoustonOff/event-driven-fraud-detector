import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.kafka.consumer import DEFAULT_DAILY_LIMIT, DEFAULT_MONTHLY_LIMIT, handle_message
from tests.conftest import make_event


def make_result(amount: Decimal) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = amount
    return result


@pytest.fixture
def session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    return s


@pytest.fixture
def publish_mock():
    with patch("app.kafka.consumer.producer_manager.publish", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_limits() -> MagicMock:
    limits = MagicMock()
    limits.daily_limit = DEFAULT_DAILY_LIMIT
    limits.monthly_limit = DEFAULT_MONTHLY_LIMIT
    return limits


# Test 1: duplicate transaction is skipped before flush
async def test_duplicate_tx_skipped(session, publish_mock):
    session.scalar.side_effect = [MagicMock()]  # SpendingLog already exists
    await handle_message(make_event(), session)
    session.flush.assert_not_called()
    session.commit.assert_not_called()
    publish_mock.assert_not_called()


# Test 2: race condition — flush raises IntegrityError → rollback, no commit, no publish
async def test_integrity_error_handled(session, publish_mock):
    session.scalar.side_effect = [None]
    session.flush.side_effect = IntegrityError("UNIQUE violation", {}, Exception())
    await handle_message(make_event(), session)
    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    publish_mock.assert_not_called()


# Test 3: spending within both limits → commit, no event published
async def test_within_limits_no_event(session, publish_mock, mock_limits):
    session.scalar.side_effect = [None, mock_limits]
    session.execute.side_effect = [
        make_result(Decimal("50000.00")),   # daily: 50k < 100k
        make_result(Decimal("200000.00")),  # monthly: 200k < 500k
    ]
    await handle_message(make_event(), session)
    session.commit.assert_called_once()
    publish_mock.assert_not_called()


# Test 4: daily limit exceeded → publish with limit_type="daily"
async def test_daily_limit_exceeded(session, publish_mock, mock_limits):
    session.scalar.side_effect = [None, mock_limits]
    session.execute.side_effect = [
        make_result(Decimal("110000.00")),  # daily: 110k > 100k
        make_result(Decimal("200000.00")),  # monthly: OK
        MagicMock(),                         # UPDATE transaction
    ]
    await handle_message(make_event(), session)
    publish_mock.assert_called_once()
    event = publish_mock.call_args.args[1]
    assert event.limit_type == "daily"


# Test 5: monthly limit exceeded (daily OK) → publish with limit_type="monthly"
async def test_monthly_limit_exceeded(session, publish_mock, mock_limits):
    session.scalar.side_effect = [None, mock_limits]
    session.execute.side_effect = [
        make_result(Decimal("60000.00")),   # daily: 60k < 100k
        make_result(Decimal("520000.00")),  # monthly: 520k > 500k
        MagicMock(),                         # UPDATE transaction
    ]
    await handle_message(make_event(), session)
    publish_mock.assert_called_once()
    event = publish_mock.call_args.args[1]
    assert event.limit_type == "monthly"


# Test 6: on limit exceed → execute called 3 times (daily SUM + monthly SUM + UPDATE)
async def test_transaction_blocked_on_exceed(session, publish_mock, mock_limits):
    session.scalar.side_effect = [None, mock_limits]
    session.execute.side_effect = [
        make_result(Decimal("110000.00")),
        make_result(Decimal("200000.00")),
        MagicMock(),
    ]
    await handle_message(make_event(), session)
    assert session.execute.call_count == 3


# Test 7: LimitExceededEvent has correct fields
async def test_limit_event_payload(session, publish_mock, mock_limits):
    tx_id = uuid.uuid4()
    session.scalar.side_effect = [None, mock_limits]
    session.execute.side_effect = [
        make_result(Decimal("110000.00")),
        make_result(Decimal("200000.00")),
        MagicMock(),
    ]
    await handle_message(make_event(transaction_id=tx_id, user_id=7), session)
    publish_mock.assert_called_once()
    topic, event = publish_mock.call_args.args
    assert topic == "limit_exceeded"
    assert event.transaction_id == tx_id
    assert event.user_id == 7
    assert event.limit_type == "daily"
    assert event.current_spent == Decimal("110000.00")
    assert event.limit_value == DEFAULT_DAILY_LIMIT


# Test 8: no UserLimit in DB → DEFAULT constants used
async def test_no_user_limits_uses_defaults(session, publish_mock):
    session.scalar.side_effect = [None, None]  # no duplicate, no UserLimit row
    session.execute.side_effect = [
        make_result(Decimal("110000.00")),  # daily > DEFAULT_DAILY_LIMIT (100k)
        make_result(Decimal("200000.00")),
        MagicMock(),
    ]
    await handle_message(make_event(), session)
    publish_mock.assert_called_once()
    event = publish_mock.call_args.args[1]
    assert event.limit_value == DEFAULT_DAILY_LIMIT
