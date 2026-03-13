FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace definition
COPY pyproject.toml uv.lock* ./
COPY packages/utils/pyproject.toml packages/utils/pyproject.toml
COPY packages/database/pyproject.toml packages/database/pyproject.toml
COPY packages/nlu/pyproject.toml packages/nlu/pyproject.toml
COPY packages/ai-engine/pyproject.toml packages/ai-engine/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/telegram-bot/pyproject.toml apps/telegram-bot/pyproject.toml

RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

COPY packages/ packages/
COPY apps/telegram-bot/ apps/telegram-bot/

CMD ["uv", "run", "python", "-m", "apps.telegram_bot.main"]
