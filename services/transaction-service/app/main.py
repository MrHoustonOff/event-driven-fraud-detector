from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import engine
from app.routes.transactions import router as transactions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


app = FastAPI(
    title="Transaction Service",
    description="Сервис приёма и хранения банковских транзакций. "
    "Входная точка системы мониторинга фрода.",
    version="0.1.0",
)

app.include_router(transactions_router)


@app.get("/health", tags=["Служебные"], summary="Проверка работоспособности")
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
