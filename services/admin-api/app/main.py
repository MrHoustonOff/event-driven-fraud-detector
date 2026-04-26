from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.limits import router as limits_router
from app.routes.rules import router as rules_router
from app.routes.users import router as users_router

app = FastAPI(title="Admin API")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rules_router)
app.include_router(limits_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
