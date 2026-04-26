import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine as db_engine
from app.kafka.consumer import consume_loop
from app.kafka.producer import producer_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await producer_manager.start()
    task = asyncio.create_task(consume_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await producer_manager.stop()
    await db_engine.dispose()


app = FastAPI(title="Fraud Detector", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["Служебные"])
async def health():
    return {"status": "ok"}
