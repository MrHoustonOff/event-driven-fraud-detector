import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.session import get_session
from app.main import app
from app.models import Base
from shared.schemas import AlertEvent, LimitExceededEvent

TEST_DATABASE_URL = settings.database_url


def make_alert_event(
    transaction_id: uuid.UUID | None = None,
    user_id: int = 1,
    fraud_score: int = 75,
) -> AlertEvent:
    return AlertEvent(
        transaction_id=transaction_id or uuid.uuid4(),
        user_id=user_id,
        fraud_score=fraud_score,
        triggered_rules=["LargeAmountRule", "NewCountryRule"],
        created_at=datetime.now(timezone.utc),
    )


def make_limit_event(
    transaction_id: uuid.UUID | None = None,
    user_id: int = 1,
) -> LimitExceededEvent:
    return LimitExceededEvent(
        transaction_id=transaction_id or uuid.uuid4(),
        user_id=user_id,
        limit_type="daily",
        current_spent=Decimal("110000.00"),
        limit_value=Decimal("100000.00"),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
async def client():
    engine = create_async_engine(TEST_DATABASE_URL)
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS notify"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(client: AsyncClient) -> AsyncSession:
    engine = create_async_engine(TEST_DATABASE_URL)
    TestSession = async_sessionmaker(engine, expire_on_commit=False)
    async with TestSession() as session:
        yield session
    await engine.dispose()
