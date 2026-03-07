# Agents

## Cursor Cloud specific instructions

### Overview

Awaqi is an AI-powered tax support chatbot (Ethiopian Revenue Authority). It's a monorepo with:
- **FastAPI backend** (`apps/api`) — Python 3.12+, managed by `uv`
- **Next.js frontend** (`apps/web`) — Node.js 18+, managed by `npm`
- **Shared Python packages** in `packages/` (database, ai-engine, nlu, utils)
- **Infrastructure**: PostgreSQL 16 + pgvector, Redis 7

### Starting infrastructure

PostgreSQL and Redis run via Docker Compose:
```bash
sudo dockerd &>/tmp/dockerd.log &  # if Docker daemon isn't running
sudo docker compose -f docker/docker-compose.yml up -d db redis
```

### Running database migrations

```bash
cd packages/database && uv run alembic upgrade head
```

### Starting the FastAPI backend (from repo root)

```bash
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```
Health check: `GET http://localhost:8000/health` returns `{"status":"ok","service":"api"}`.

### Starting the Next.js frontend

Required env vars before running:
```bash
export BETTER_AUTH_SECRET="$(openssl rand -base64 32)"
export DATABASE_URL_SYNC="postgresql://user:password@localhost:5432/awaqi_db"
export NEXT_PUBLIC_APP_URL="http://localhost:3000"
export NEXT_PUBLIC_API_URL="http://localhost:8000"
```
Then:
```bash
cd apps/web && npm run dev
```

### Lint & type-check

- Python: `uv run ruff check .` (pre-existing import-sorting warnings exist in `apps/api/`)
- TypeScript: `cd apps/web && npx tsc --noEmit`
- No ESLint config is set up yet; `npm run lint` triggers an interactive first-time setup prompt — avoid it in CI.
- No automated test files exist in the repo yet.

### Gotchas

- The `uv run uvicorn` command **must** be run from the repo root — the module path is `apps.api.main:app`.
- The chat endpoint `POST /v1/chat/send` requires `session_id` as a valid UUID string (not null).
- The AI-engine RAG pipeline is a placeholder — chat returns a stub response with `confidence_score: 0.0`.
- The `docker-compose.yml` has a `version: '3.8'` attribute that triggers a deprecation warning (harmless).
- The `Makefile` `check` target runs `cd apps/web && npm run build` (Next.js build), not lint-only.
