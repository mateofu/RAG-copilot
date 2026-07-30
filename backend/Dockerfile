FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/app \
    UV_CACHE_DIR=/app/.cache/uv \
    UV_FROZEN=1 \
    UV_NO_DEV=1 \
    UV_NO_SYNC=1
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /app/.cache/uv /app/data/documents \
    && chown -R app:app /app
USER app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
