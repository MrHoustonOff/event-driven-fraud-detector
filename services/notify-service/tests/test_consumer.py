import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.kafka.consumer import handle_message
from tests.conftest import make_alert_event, make_limit_event


@pytest.fixture
def session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    return s


@pytest.fixture
def http_client() -> AsyncMock:
    client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    client.post.return_value = mock_resp
    return client


# Test 1: AlertEvent → status="sent", notification_type="fraud_alert"
async def test_alert_sent_successfully(session, http_client):
    await handle_message(make_alert_event(), "fraud_alert", session, http_client)
    notification = session.add.call_args.args[0]
    assert notification.status == "sent"
    assert notification.notification_type == "fraud_alert"
    assert notification.error_message is None
    session.commit.assert_called_once()


# Test 2: LimitExceededEvent → status="sent", notification_type="limit_exceeded"
async def test_limit_exceeded_sent_successfully(session, http_client):
    await handle_message(make_limit_event(), "limit_exceeded", session, http_client)
    notification = session.add.call_args.args[0]
    assert notification.status == "sent"
    assert notification.notification_type == "limit_exceeded"
    session.commit.assert_called_once()


# Test 3: webhook returns 5xx → status="failed", error_message set
async def test_webhook_http_error(session, http_client):
    http_client.post.return_value.status_code = 500
    await handle_message(make_alert_event(), "fraud_alert", session, http_client)
    notification = session.add.call_args.args[0]
    assert notification.status == "failed"
    assert notification.error_message == "HTTP 500"
    session.commit.assert_called_once()


# Test 4: webhook raises exception → status="failed", error_message contains error text
async def test_webhook_connection_error(session, http_client):
    http_client.post.side_effect = Exception("Connection refused")
    await handle_message(make_alert_event(), "fraud_alert", session, http_client)
    notification = session.add.call_args.args[0]
    assert notification.status == "failed"
    assert "Connection refused" in notification.error_message
    session.commit.assert_called_once()


# Test 5: payload contains fields from the original event
async def test_notification_payload_correct(session, http_client):
    tx_id = uuid.uuid4()
    event = make_alert_event(transaction_id=tx_id, user_id=7, fraud_score=85)
    await handle_message(event, "fraud_alert", session, http_client)
    notification = session.add.call_args.args[0]
    assert notification.user_id == 7
    assert str(tx_id) in str(notification.payload)
    assert notification.payload["fraud_score"] == 85


# Test 6: commit is always called even on webhook failure
async def test_commit_always_called(session, http_client):
    http_client.post.side_effect = Exception("timeout")
    await handle_message(make_alert_event(), "fraud_alert", session, http_client)
    session.commit.assert_called_once()
