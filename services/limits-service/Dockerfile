FROM python:3.13-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY shared/ ./shared/
WORKDIR /app/services/limits-service
COPY services/limits-service/pyproject.toml services/limits-service/uv.lock* ./
RUN uv sync --frozen --no-dev
COPY services/limits-service/app/ ./app/
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
