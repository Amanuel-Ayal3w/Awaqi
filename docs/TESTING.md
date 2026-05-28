# Testing Guide

Awaqi uses a three-layer test strategy: **unit**, **integration**, and **end-to-end (E2E)**.

| Layer | Tool | Scope | Needs DB? |
|-------|------|-------|-----------|
| Python unit | pytest | schemas, NLU, ai-engine helpers | No |
| Python integration | pytest + httpx | FastAPI routes, auth, chat | Yes (`awaqi_db_test`) |
| Frontend unit | Vitest + Testing Library | utils, components, route helpers | No |
| E2E | Playwright | browser flows + API smoke | Yes (for full stack) |

We use **Playwright** for browser automation (recommended for Next.js). Selenium and Cypress are not configured; Playwright covers the same scenarios with better Next.js support.

## Quick commands

From the repo root:

```bash
make test-unit          # Python unit tests only
make test-integration   # Python API tests (PostgreSQL required)
make test               # All Python tests
make test-web           # Vitest (frontend unit)
make test-e2e           # Playwright (starts API + web if not running)
make check              # lint + all Python tests + Next build + Vitest
```

## Python tests

### Setup

```bash
uv sync --group dev
make test-db   # creates awaqi_db_test if missing
```

Integration tests **refuse** to run against any database other than `awaqi_db_test`. Override with:

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/awaqi_db_test"
```

### Run

```bash
uv run --package api pytest tests/ -v
uv run --package api pytest tests/api/test_health.py -v   # single file
uv run --package api pytest -m integration -v             # if tests are marked
```

### Layout

- `tests/api/` — FastAPI integration tests (`client` fixture, mocked embedder)
- `tests/packages/` — shared package unit tests
- `packages/ai-engine/tests/` — scraper, chunker, RAG helpers

### Writing integration tests

Use fixtures from `tests/conftest.py`: `client`, `admin_user`, `admin_session`, `db_session`.

Embedder calls are auto-mocked in `tests/api/conftest.py`. Use `@pytest.mark.real_embedder` only when you intentionally need the real embedder.

## Frontend unit tests (Vitest)

From `apps/web`:

```bash
npm test              # single run
npm run test:watch    # watch mode
```

Tests live next to source: `*.test.ts`, `*.test.tsx`.

## E2E tests (Playwright)

Install browsers once:

```bash
cd apps/web && npx playwright install chromium
```

Run (auto-starts backend on :8000 and Next.js on :3100 unless already up):

```bash
cd apps/web && npm run test:e2e
npm run test:e2e:ui     # interactive UI mode
```

Specs: `apps/web/e2e/*.spec.ts`.

For local debugging with servers already running (`./start.web.sh`, `make back`), Playwright reuses them when `CI` is unset.

## CI

GitHub Actions (`.github/workflows/ci.yml`):

- `test-python` — unit tests, no Postgres service
- `test-integration` — Postgres service + API tests
- `test-web` — Vitest
- `test-e2e` — Playwright with Postgres (optional smoke)
- `build-web` — production build

## Choosing E2E vs integration

- Prefer **integration tests** for API contracts, auth, and DB behavior (fast, no browser).
- Use **E2E** for critical user journeys (landing page, login redirects, multi-page flows).
- Avoid duplicating the same assertion in both layers.
