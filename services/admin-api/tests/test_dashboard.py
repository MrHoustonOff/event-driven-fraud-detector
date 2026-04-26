import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction


# Test 1: dashboard when DB is empty
async def test_dashboard_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["transactions_today"] == 0
    assert data["alerts_today"] == 0
    assert data["blocked_today"] == 0
    assert data["top_fraud_score"] == []


# Test 2: without token → 401
async def test_dashboard_unauthenticated(client: AsyncClient):
    assert (await client.get("/dashboard")).status_code == 401


# Test 3: blocked transaction appears in metrics and top list
async def test_dashboard_with_data(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    tx = Transaction(
        id=uuid.uuid4(),
        user_id=1,
        amount=Decimal("52000"),
        currency="RUB",
        country="TH",
        city="Bangkok",
        merchant="Casino",
        status="BLOCKED",
        fraud_score=85,
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(tx)
    await db_session.commit()

    resp = await client.get("/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["transactions_today"] == 1
    assert data["blocked_today"] == 1
    assert len(data["top_fraud_score"]) == 1
    assert data["top_fraud_score"][0]["fraud_score"] == 85
