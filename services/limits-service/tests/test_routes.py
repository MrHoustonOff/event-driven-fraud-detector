import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from app.models import SpendingLog, UserLimit
from tests.conftest import make_event  # noqa: F401 — imported to satisfy type hints


# Test 1: no UserLimit row → returns defaults
async def test_get_limits_no_record_returns_defaults(client: AsyncClient):
    resp = await client.get("/limits/99")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 99
    assert Decimal(data["daily_limit"]) == Decimal("100000.00")
    assert Decimal(data["monthly_limit"]) == Decimal("500000.00")
    assert Decimal(data["spent_today"]) == Decimal("0.00")
    assert Decimal(data["spent_this_month"]) == Decimal("0.00")


# Test 2: existing UserLimit row → returns stored values
async def test_get_limits_existing_record(client: AsyncClient, db_session):
    await db_session.execute(
        insert(UserLimit).values(
            user_id=1,
            daily_limit=Decimal("50000.00"),
            monthly_limit=Decimal("300000.00"),
        )
    )
    await db_session.commit()

    resp = await client.get("/limits/1")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["daily_limit"]) == Decimal("50000.00")
    assert Decimal(data["monthly_limit"]) == Decimal("300000.00")


# Test 3: PUT for new user → creates record, GET reflects new values
async def test_put_limits_creates_record(client: AsyncClient):
    resp = await client.put("/limits/2", json={"daily_limit": "75000.00"})
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["daily_limit"]) == Decimal("75000.00")
    assert Decimal(data["monthly_limit"]) == Decimal("500000.00")  # default

    get_resp = await client.get("/limits/2")
    assert Decimal(get_resp.json()["daily_limit"]) == Decimal("75000.00")


# Test 4: PUT updates existing record without touching unchanged fields
async def test_put_limits_updates_existing(client: AsyncClient, db_session):
    await db_session.execute(
        insert(UserLimit).values(
            user_id=3,
            daily_limit=Decimal("50000.00"),
            monthly_limit=Decimal("300000.00"),
        )
    )
    await db_session.commit()

    resp = await client.put("/limits/3", json={"monthly_limit": "400000.00"})
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["daily_limit"]) == Decimal("50000.00")   # unchanged
    assert Decimal(data["monthly_limit"]) == Decimal("400000.00")  # updated


# Test 5: spent_today reflects only today's spending_log entries
async def test_get_limits_spent_today_accurate(client: AsyncClient, db_session):
    uid = 4
    await db_session.execute(
        insert(SpendingLog).values([
            {
                "user_id": uid,
                "amount": Decimal("15000.00"),
                "transaction_id": uuid.uuid4(),
                "created_at": datetime.now(timezone.utc),
            },
            {
                "user_id": uid,
                "amount": Decimal("20000.00"),
                "transaction_id": uuid.uuid4(),
                "created_at": datetime.now(timezone.utc),
            },
        ])
    )
    await db_session.commit()

    resp = await client.get(f"/limits/{uid}")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["spent_today"]) == Decimal("35000.00")
    assert Decimal(data["spent_this_month"]) == Decimal("35000.00")
