FROM python:3.13-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY shared/ ./shared/
WORKDIR /app/services/fraud-detector
COPY services/fraud-detector/pyproject.toml services/fraud-detector/uv.lock* ./
RUN uv sync --frozen --no-dev
COPY services/fraud-detector/app/ ./app/
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
