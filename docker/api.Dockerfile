FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace definition first (for caching)
COPY pyproject.toml uv.lock* ./
COPY packages/utils/pyproject.toml packages/utils/pyproject.toml
COPY packages/database/pyproject.toml packages/database/pyproject.toml
COPY packages/nlu/pyproject.toml packages/nlu/pyproject.toml
COPY packages/ai-engine/pyproject.toml packages/ai-engine/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/telegram-bot/pyproject.toml apps/telegram-bot/pyproject.toml

# Install dependencies (cached unless pyproject.toml changes)
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy full source
COPY packages/ packages/
COPY apps/api/ apps/api/

EXPOSE 8000

# Run migrations then start the API
CMD ["sh", "-c", "cd packages/database && uv run alembic upgrade head && cd /app && uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"]
