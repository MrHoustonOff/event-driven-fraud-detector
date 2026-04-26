from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.kafka.consumer import handle_message
from shared.schemas import AlertEvent

from tests.conftest import make_event


async def test_tx_not_found(session, publish_mock):
    session.scalar.return_value = None
    await handle_message(make_event(), session)

    session.execute.assert_not_called()
    session.commit.assert_not_called()
    publish_mock.assert_not_called()


async def test_already_processed(session, publish_mock, pending_tx):
    pending_tx.status = "APPROVED"
    await handle_message(make_event(), session)

    session.commit.assert_not_called()
    publish_mock.assert_not_called()


async def test_approved_no_alert(session, publish_mock):
    with patch("app.kafka.consumer._engine.evaluate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = (30, [])
        await handle_message(make_event(), session)

    session.commit.assert_called_once()
    publish_mock.assert_not_called()


async def test_flagged_boundary(session, publish_mock):
    with patch("app.kafka.consumer._engine.evaluate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = (50, ["LargeAmountRule"])
        await handle_message(make_event(), session)

    session.commit.assert_called_once()
    publish_mock.assert_called_once()
    alert: AlertEvent = publish_mock.call_args.args[1]
    assert alert.fraud_score == 50


async def test_blocked_boundary(session, publish_mock):
    with patch("app.kafka.consumer._engine.evaluate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = (70, ["NewCountryRule", "LargeAmountRule"])
        await handle_message(make_event(), session)

    session.commit.assert_called_once()
    publish_mock.assert_called_once()
    alert: AlertEvent = publish_mock.call_args.args[1]
    assert alert.fraud_score == 70


async def test_alert_payload(session, publish_mock):
    event = make_event()
    triggered = ["LargeAmountRule", "NewCountryRule"]
    with patch("app.kafka.consumer._engine.evaluate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = (75, triggered)
        await handle_message(event, session)

    publish_mock.assert_called_once()
    topic: str = publish_mock.call_args.args[0]
    alert: AlertEvent = publish_mock.call_args.args[1]

    assert topic == "alerts"
    assert alert.transaction_id == event.transaction_id
    assert alert.user_id == event.user_id
    assert alert.fraud_score == 75
    assert alert.triggered_rules == triggered


async def test_commit_called_on_happy_path(session, publish_mock):
    with patch("app.kafka.consumer._engine.evaluate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = (0, [])
        await handle_message(make_event(), session)

    session.commit.assert_called_once()
