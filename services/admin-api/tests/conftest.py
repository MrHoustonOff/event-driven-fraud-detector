import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.session import get_session
from app.main import app
from app.models import Base

SCHEMAS = ["auth", "fraud", "limits", "transactions", "notify"]


@pytest.fixture
async def db_engine() -> AsyncEngine:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for schema in SCHEMAS:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(db_engine: AsyncEngine) -> AsyncClient:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def db_session(db_engine: AsyncEngine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict:
    await client.post("/auth/register", json={"username": "testadmin", "password": "password123"})
    return {"username": "testadmin", "password": "password123"}


@pytest.fixture
async def auth_headers(client: AsyncClient, registered_user: dict) -> dict:
    resp = await client.post("/auth/login", json=registered_user)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def seeded_rule(client: AsyncClient, auth_headers: dict) -> dict:
    resp = await client.post(
        "/rules",
        json={"name": "TestRule", "weight": 30},
        headers=auth_headers,
    )
    return resp.json()
