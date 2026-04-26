FROM python:3.13-slim
RUN pip install uv
WORKDIR /app/services/admin-api
COPY services/admin-api/pyproject.toml services/admin-api/uv.lock* ./
RUN uv sync --frozen --no-dev
COPY services/admin-api/app/ ./app/
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
