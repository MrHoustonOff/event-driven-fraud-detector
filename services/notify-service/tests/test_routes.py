import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from app.models import Notification


# Test 1: no records → 200, empty list
async def test_get_notifications_empty(client: AsyncClient):
    resp = await client.get("/notifications?user_id=99")
    assert resp.status_code == 200
    assert resp.json() == []


# Test 2: seeded records returned in DESC order
async def test_get_notifications_returns_records(client: AsyncClient, db_session):
    await db_session.execute(
        insert(Notification).values([
            {"user_id": 1, "notification_type": "fraud_alert", "payload": {"score": 75}, "status": "sent"},
            {"user_id": 1, "notification_type": "limit_exceeded", "payload": {"type": "daily"}, "status": "sent"},
        ])
    )
    await db_session.commit()

    resp = await client.get("/notifications?user_id=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["notification_type"] == "limit_exceeded"  # DESC — последняя вставленная первая


# Test 3: filters by user_id — other users not returned
async def test_get_notifications_filters_by_user(client: AsyncClient, db_session):
    await db_session.execute(
        insert(Notification).values([
            {"user_id": 1, "notification_type": "fraud_alert", "payload": {}, "status": "sent"},
            {"user_id": 2, "notification_type": "fraud_alert", "payload": {}, "status": "sent"},
        ])
    )
    await db_session.commit()

    resp = await client.get("/notifications?user_id=1")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1


# Test 4: limit param is respected
async def test_get_notifications_limit_param(client: AsyncClient, db_session):
    await db_session.execute(
        insert(Notification).values([
            {"user_id": 1, "notification_type": "fraud_alert", "payload": {"i": i}, "status": "sent"}
            for i in range(5)
        ])
    )
    await db_session.commit()

    resp = await client.get("/notifications?user_id=1&limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3
