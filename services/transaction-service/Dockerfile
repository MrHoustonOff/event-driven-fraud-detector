FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Mirror monorepo layout so ../../shared resolves to /app/shared/
COPY shared/ ./shared/

WORKDIR /app/services/transaction-service
COPY services/transaction-service/pyproject.toml services/transaction-service/uv.lock* ./
RUN uv sync --frozen --no-dev

COPY services/transaction-service/app/ ./app/

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
