import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine as db_engine
from app.kafka.consumer import consume_loop
from app.routes.notifications import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(consume_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await db_engine.dispose()


app = FastAPI(title="Notify Service", version="0.1.0", lifespan=lifespan)

app.include_router(router)


@app.get("/health", tags=["Служебные"])
async def health():
    return {"status": "ok"}
