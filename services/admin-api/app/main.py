import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.limits import router as limits_router
from app.routes.rules import router as rules_router
from app.routes.users import router as users_router


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
_handler.setFormatter(_JsonFormatter("admin-api"))
logging.basicConfig(level=logging.INFO, handlers=[_handler], force=True)

app = FastAPI(title="Admin API")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rules_router)
app.include_router(limits_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
