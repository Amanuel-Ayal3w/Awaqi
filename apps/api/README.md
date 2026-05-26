# Awaqi API

FastAPI backend for the Awaqi regulatory-assistant platform. Provides chat, document management, admin, and scraper endpoints.

## Architecture

```
apps/api/
├── main.py          # FastAPI app, CORS, router mounts
├── deps.py          # Auth dependencies (get_current_admin, get_current_customer)
├── schemas.py       # Pydantic request/response models
└── routers/
    ├── chat.py      # /v1/chat/* — send messages, history, feedback
    └── admin.py     # /v1/admin/* — users, uploads, logs, scraper (protected)
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL + Redis running (see below)

## Setup & Run

### 1. Start infrastructure

**Option A — Docker (recommended for teams):**

From the repo root:

```bash
docker compose -f docker/docker-compose.yml up -d db redis
```

This gives you PostgreSQL (`awaqi_db`) on `:5432` and Redis on `:6379`.

**Option B — Local installs (if Docker is unavailable):**

Install and start both services natively:

```bash
# PostgreSQL (Ubuntu/Debian)
sudo apt install postgresql
sudo systemctl start postgresql
sudo -u postgres createdb awaqi_db

# Redis (Ubuntu/Debian)
sudo apt install redis-server
sudo systemctl start redis-server

# Verify Redis is up
redis-cli ping   # should return PONG
```

On macOS use `brew install postgresql redis` and `brew services start ...`.

> **Configure the connection** via environment variables before starting the API:
> ```bash
> export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/awaqi_db
> export REDIS_URL=redis://localhost:6379/0
> ```
> You can also put these in a `.env` file at the repo root — `uv` will pick them up automatically.

### 2. Install dependencies

```bash
# From repo root — installs all workspace packages
uv sync
```

### 3. Run migrations

```bash
cd packages/database
uv run alembic upgrade head
```

### 4. Start the server

**From the repo root** (not from `apps/api/`):

```bash
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

The module path is `apps.api.main:app` because `uv` resolves imports from the workspace root.

The API will be available at `http://localhost:8000`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost:5432/awaqi_db` | Async PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `ALLOWED_ORIGINS` | `http://localhost:3100,http://127.0.0.1:3100` | Comma-separated CORS origins |
| `SCRAPER_SCHEDULER_ENABLED` | `true` | When `true`, the API starts a daily MoR scrape job (default **00:00** `Africa/Addis_Ababa`) |
| `SCRAPER_CRON_HOUR` | `0` | Cron hour for scheduled scrape (overridable via admin UI / `scraper_config` table) |
| `SCRAPER_CRON_MINUTE` | `0` | Cron minute for scheduled scrape |
| `MOR_API_BASE_URL` | `https://www.mor.gov.et/api` | MoR JSON API base (SPA loads PDFs from here) |
| `MOR_SCRAPE_SEED_URLS` | Six law listing pages (see `.env.example`) | Frontend routes mapped to API discovery families |
| `MOR_SCRAPE_MAX_LINKS` | `30` | Max PDFs downloaded / ingested per run |
| `DOCUMENT_STORAGE_DIR` | `./data/documents` | On-disk storage for scraped PDF bytes |
| `MOR_SCRAPER_USER_AGENT` | `AwaqiBot/1.0 (...)` | HTTP User-Agent for outbound scraper requests |
| `MOR_HTTP_SSL_VERIFY` | `false` | Set `true` to verify MoR HTTPS certs; default `false` because mor.gov.et often fails Python TLS on macOS |
| `OCR_LANGS` | `eng+amh` | Tesseract languages for scanned PDF fallback — **`amh` traineddata must be installed** (`apt install tesseract-ocr-amh` or `brew install tesseract-lang`) |
| `OCR_RENDER_SCALE` | `3.0` | PDF page render scale before OCR (higher = slower, often better for Amharic) |

### Telegram channel scraper (@morwestaa)

**Bot API cannot read channel history.** Scraping uses [Telethon](https://docs.telethon.dev/) (MTProto) with a user session.

| Variable | Description |
|----------|-------------|
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | From https://my.telegram.org/apps |
| `TELEGRAM_SESSION_STRING` | Run `uv run python scripts/telegram_gen_session.py` |
| `TELEGRAM_CHANNEL` | Default `morwestaa` |
| `TELEGRAM_SCRAPE_SINCE` | Default `2026-04-01` (only posts on/after this date) |

Admin: `POST /v1/admin/telegram/scrape`, `GET /v1/admin/telegram/messages`, config at `/v1/admin/telegram/config`.

## Endpoints

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Returns `{"status": "ok", "service": "api"}` |

### Chat (`/v1/chat`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/v1/chat/send` | None | Send a message and get an AI response; returns a signed `session_token` |
| `GET` | `/v1/chat/history/{session_id}` | `X-Session-Token` (guest) | Retrieve message history for a session |
| `POST` | `/v1/chat/feedback/{message_id}` | None | Submit thumbs-up/down feedback on a message |

### Admin (`/v1/admin`) — all routes require a valid session token

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/v1/admin/users` | Admin | List all admin users |
| `DELETE` | `/v1/admin/users/{user_id}` | Admin | Delete an admin user |
| `POST` | `/v1/admin/upload` | Admin | Upload a document (PDF) for ingestion |
| `GET` | `/v1/admin/logs` | Admin | Fetch recent user query logs |
| `POST` | `/v1/admin/scrape` | Superadmin | Run one MoR scrape cycle (same entrypoint as the scheduled job) |
| `GET` | `/v1/admin/scraper/status` | Superadmin | Scheduler enabled, cron time, next run, last run |
| `GET` | `/v1/admin/scraper/runs` | Superadmin | Scrape run history |
| `GET` | `/v1/admin/scraper/config` | Superadmin | Current scraper configuration |
| `PATCH` | `/v1/admin/scraper/config` | Superadmin | Update seeds, cron, limits; reschedules job |
| `GET` | `/v1/admin/documents/{doc_id}/content` | Admin | Extracted text preview (chunks or live OCR) |
| `GET` | `/v1/admin/documents/{doc_id}/file` | Admin | Download / inline PDF (disk or source URL) |
| `POST` | `/v1/admin/documents/{doc_id}/retry-ingest` | Admin | Re-run OCR from stored PDF (`?force_index=true` optional) |

## Authentication

Admin endpoints are protected by the `get_current_admin` dependency in `deps.py`. It validates a Better Auth session token by querying `ba_session` + `ba_user` in PostgreSQL — no JWT or shared secret needed.

The token can be provided as:
- `Authorization: Bearer <token>` header
- `better-auth.session_token` cookie (set automatically by the Next.js frontend)

Guest chat sessions are protected with a server-signed token:
- `POST /v1/chat/send` returns `session_token`
- Clients must send `X-Session-Token: <session_token>` when reusing a guest `session_id` and when calling `GET /v1/chat/history/{session_id}`

### Request/Response Schemas

Defined in `schemas.py`:

| Schema | Used by |
|---|---|
| `ChatRequest` | `POST /v1/chat/send` — `{message, session_id, language?}` |
| `ChatResponse` | Response — `{response_text, citations[], confidence_score, session_token?}` |
| `ChatMessage` | `GET /v1/chat/history/*` — `{role, content, timestamp}` |
| `FeedbackRequest` | `POST /v1/chat/feedback/*` — `{score, comment?}` |
| `DocumentStatus` | `POST /v1/admin/upload` — `{doc_id, status}` |
| `LogEntryList` | `GET /v1/admin/logs` — `{logs: [{timestamp, level, message}]}` |
| `AdminScrapeResult` | `POST /v1/admin/scrape` — `{status, stats: {discovered, inserted, skipped, errors}}` |
| `AdminScraperStatus` | `GET /v1/admin/scraper/status` |
| `AdminScraperRunList` | `GET /v1/admin/scraper/runs` |
| `AdminScraperConfig` | `GET/PATCH /v1/admin/scraper/config` |
| `AdminUserList` | `GET /v1/admin/users` — `{users: [{id, name, email, role, is_active, created_at}]}` |

## Interactive Docs

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
