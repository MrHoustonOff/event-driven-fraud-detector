from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20,      # было 5 (default) — при 300 users достигался предел
    max_overflow=0,    # фиксированный пул: предсказуем, нет connection storm
    pool_timeout=30,   # явный timeout ожидания соединения из пула
    pool_recycle=1800, # переоткрывать соединения каждые 30 мин (против stale TCP)
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
