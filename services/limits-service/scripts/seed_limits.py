"""
Seed default limits for user_id 1-10.
Run: cd services/limits-service && uv run python scripts/seed_limits.py
Requires DATABASE_URL in .env or environment.
"""
import asyncio
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import UserLimit
from sqlalchemy.dialects.postgresql import insert as pg_insert


async def seed() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for user_id in range(1, 11):
            stmt = pg_insert(UserLimit).values(
                user_id=user_id,
                daily_limit=Decimal("100000.00"),
                monthly_limit=Decimal("500000.00"),
            ).on_conflict_do_nothing(index_elements=["user_id"])
            await conn.execute(stmt)
    await engine.dispose()
    logging.getLogger(__name__).info("seeded limits for user_id 1-10")


if __name__ == "__main__":
    asyncio.run(seed())
