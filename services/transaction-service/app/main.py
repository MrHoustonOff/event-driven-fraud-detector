import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.db.session import engine
from app.kafka.producer import producer_manager
from app.routes.transactions import router as transactions_router


class _JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter("transaction-service"))
logging.basicConfig(level=logging.INFO, handlers=[_handler], force=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await producer_manager.start()
    yield
    await producer_manager.stop()
    await engine.dispose()


app = FastAPI(
    title="Transaction Service",
    description="Сервис приёма и хранения банковских транзакций. "
    "Входная точка системы мониторинга фрода.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(transactions_router)


@app.get("/health", tags=["Служебные"], summary="Проверка работоспособности")
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
