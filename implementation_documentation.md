# Implementation Documentation

**Project:** Awaqi — LLM-Based Support Bot for the Ethiopian Revenue Authority
**Repository:** ba5liel/Awaqi (monorepo)
**Phase:** Implementation
**Version:** 1.0

---

## 1. Document Control

### 1.1 Document Information

| Field | Value |
|---|---|
| Project name | Awaqi (LLM-Based Support Bot for ERA) |
| Document title | Implementation Documentation |
| Version | 1.0 |
| Authors | Group 13 — Abdurahman M., Amanuel A., Basliel S., Bethel W., Diborah D. |
| Reviewer | Mr. Daniel Abebe (Advisor) |
| Approval date | 2026-05-27 |
| Classification | Internal — academic submission |
| Related docs | SRS v1.1 (Final Updated), SDS v1.1 (Final Updated), ARCHITECTURE.md |

### 1.2 Revision History

| Date | Version | Author | Description |
|---|---|---|---|
| 2026-05-27 | 1.0 | Group 13 | First implementation document, written against the deployed Awaqi build |

---

## 2. Introduction

### 2.1 Purpose of the Document

This document records how the Awaqi system was actually built and deployed. The SRS describes *what* the system should do and the SDS describes *how* it is designed; this document describes *what we did* — the code layout, the infrastructure, the configuration, the pipelines, and the operational procedures that turn the design into a running service.

It is written for three audiences:

1. The engineering team that maintains the system after the project handover.
2. The advisor and graders, who need to verify that the build matches the requirements.
3. Future contributors who will pick up the codebase and need a single document that points them to the relevant pieces.

### 2.2 Project Overview

Awaqi is an AI-powered information desk agent for the Ethiopian Revenue Authority (ERA, formerly MoR). Taxpayers ask questions in Amharic or English through a web chat or a Telegram bot. The system answers using a Retrieval-Augmented Generation (RAG) pipeline grounded on regulatory documents scraped from `mor.gov.et` and uploaded by administrators.

The system uses hybrid retrieval (dense pgvector search plus PostgreSQL full-text search, fused with Reciprocal Rank Fusion) and a Gemini chat model for generation, with an extractive fallback when generation fails or is unavailable. Citations are mandatory for every factual response.

### 2.3 Implementation Scope

**Included components**

- **Frontend (web):** Next.js 15 chat interface, admin dashboard, Better Auth login flows, multilingual UX (Amharic + English) via `next-intl`.
- **Backend (API):** FastAPI service exposing chat, admin, and Telegram-link routers. Async SQLAlchemy + Alembic for the database layer.
- **AI engine:** Embedding generation (Gemini), hybrid retrieval, RRF fusion, RAG answer synthesis, extractive fallback, query NLU heuristics.
- **Ingestion pipeline:** PDF/HTML extraction, OCR fallback (PyMuPDF + Tesseract or Gemini Flash), token chunking, atomic chunk replacement.
- **Telegram bot:** Pyrogram-based bot that forwards messages to the API and renders cited responses.
- **Scraper:** APScheduler-driven daily job against `mor.gov.et`.
- **Infrastructure:** Docker images for `api`, `web`, `db` (pgvector), `redis`, `telegram-bot`. Single EC2 host, Nginx reverse proxy, Certbot TLS, Cloudflare in front for WAF and DNS.
- **Security controls:** Better Auth sessions (admin + customer), HMAC-signed guest session tokens, Redis token-bucket rate limiting, TLS everywhere.
- **CI/CD:** GitHub Actions running Ruff, type checks, unit tests, and integration tests against an ephemeral pgvector Postgres.

**Excluded from this release**

The Amharic intent and entity classification pipeline was scoped out. Initial experiments with XLM-RoBERTa and the local heuristic classifier underperformed on the Amharic dataset we had available (well below the 90% target in NFR-08), and the team decided that shipping a weak classifier was worse than not shipping one. The hooks for intent are still in the schema and in the NLU module, but the model is disabled.

Other deferrals from the SRS (immutable audit log, hard confidence-threshold gating, full feedback UX, ClamAV scanning, automated EM/F1/BERTScore evaluation) are documented in SRS section 5 and not repeated here.

---

## 3. Implementation Strategy

### 3.1 Implementation Approach

The team worked in two-week Agile sprints. Each sprint closed with a working slice deployed to the staging EC2 box. Tickets were tracked in GitHub Issues, grouped by milestone (Ingestion, Retrieval, Generation, Web UX, Telegram, Hardening).

A few practical rules that shaped the work:

- **Monorepo first.** Everything lives in one repo (`apps/*`, `packages/*`) so a change that crosses the API and the database schema lands in one PR.
- **`uv` for Python, `npm` for the web.** Lockfiles are committed. `make check` mirrors what CI runs, so contributors can reproduce CI locally before pushing.
- **Database migrations gate features.** A feature that needs a schema change is not merged until the Alembic migration is written and tested.
- **Branches:** `main` is protected; work happens on short-lived feature branches (`bas-*`, `aman-*`, etc.) that merge via PR. CI runs on push to `main`, `dev`, `telegram_bot`, and `aman-fixes`.

### 3.2 Deployment Model

The deployment is intentionally simple. We run a single AWS EC2 instance with Docker installed. PostgreSQL (with pgvector) and Redis run as Docker containers from the project's compose file. The API and the Telegram bot also run as containers. The web service runs from a built Next.js image. PM2 supervises the API and web processes inside their containers to give us automatic restarts and a unified `pm2 logs` view during incidents.

In front of all of this:

- **Nginx** terminates TLS (certificates issued by **Certbot**, auto-renewed by a cron entry) and reverse-proxies `/` to the web container and `/api/` to the FastAPI container.
- **Cloudflare** sits in front of the EC2 public address, providing DNS, DDoS mitigation, and a WAF rule set. The EC2 security group only accepts traffic from Cloudflare IPs on 443.
- **AWS security groups** further restrict access: SSH on 22 is locked to the team's static IPs, and the database/Redis ports are not exposed outside the host.

Monitoring is currently lightweight — PM2 logs are the primary observability surface, and `journalctl` covers Docker daemon issues. Prometheus + Grafana is wired up as a follow-up (see section 13); the exporters are present in compose but not enabled in the production overlay yet.

### 3.3 Environment Strategy

| Environment | Where it runs | Database | Purpose |
|---|---|---|---|
| Development | Developer laptop | Local Docker Postgres + Redis | Day-to-day coding, fast iteration |
| Testing | GitHub Actions runner | Ephemeral `pgvector/pgvector:pg16` service container | Unit + integration tests on every PR |
| Staging | Same EC2 host, different compose profile and subdomain | Same Postgres instance, separate database `awaqi_db_staging` | Manual QA, advisor demos |
| Production | EC2 (`awaqi.<domain>`) | `awaqi_db` on the same Postgres | Live system |

Staging and production share the host because the project budget does not justify two boxes. Logical isolation is through separate databases, separate Redis DB indices (`/0` for prod, `/1` for staging), and separate Better Auth secrets.

---

## 4. System Environment Setup

### 4.1 Hardware Requirements

The production EC2 instance is a `t3.medium` (2 vCPU, 4 GB RAM, 30 GB gp3 EBS). This is the working configuration that handles the current load comfortably; the LLM and embedding calls are offloaded to Gemini, so the host itself does not need GPU capacity.

| Role | Spec | Notes |
|---|---|---|
| Application host (API + web + bot) | 2 vCPU, 4 GB RAM | EC2 `t3.medium` |
| Database (Postgres + pgvector) | Same host, container | 30 GB persistent volume; nightly `pg_dump` to S3 |
| Cache (Redis) | Same host, container | Memory-only, no persistence needed |
| AI inference | External (Google Gemini API) | No local GPU |

The host is sized for the academic deployment. For a production rollout serving the volume the SRS describes (hundreds of concurrent users), the recommended upgrade path is to split Postgres onto an RDS instance, move Redis to ElastiCache, and run the API behind an Application Load Balancer across two or three application instances.

### 4.2 Software Requirements

**Operating system:** Ubuntu 22.04 LTS on the EC2 host. Local development is supported on macOS and Linux; Windows users should work inside WSL2.

**Runtimes:**

- Python 3.12 (managed via `uv`)
- Node.js 20 LTS (managed via `nvm`)
- Docker 24+ and Docker Compose v2

**Key Python dependencies** (pinned in `uv.lock`):

- `fastapi`, `uvicorn`, `pydantic`
- `sqlalchemy[asyncio]`, `alembic`, `asyncpg`, `pgvector`
- `redis`, `apscheduler`
- `google-genai` (Gemini SDK)
- `pymupdf`, `pytesseract`, `beautifulsoup4`, `httpx`
- `pyrogram` (Telegram client)
- Dev tooling: `ruff`, `pytest`, `pytest-asyncio`

**Key Node dependencies** (in `apps/web/package.json`):

- `next@15`, `react@19`, `typescript`
- `better-auth`
- `next-intl`
- `@radix-ui/*` + Tailwind CSS (shadcn/ui)

**System packages on the host:**

- `tesseract-ocr` with the Amharic language pack (`tesseract-ocr-amh`) for OCR fallback when documents are scanned images
- `nginx`, `certbot`

### 4.3 Development Tools

| Tool | Purpose |
|---|---|
| VS Code | Primary editor; `.vscode/` ships recommended extensions (Python, Ruff, ESLint, Prettier) |
| Docker Desktop | Local containers for Postgres, Redis, optional API/web |
| Git + GitHub | Source control and code review |
| `uv` | Python dependency and virtual-env manager |
| `make` | Wraps the common dev commands — see `make help` for the full list |
| `npm` | Frontend dependency manager |

Kubernetes is not part of the current toolchain. The compose stack is small enough that the operational overhead of K8s is not justified.

---

## 5. Infrastructure Implementation

### 5.1 Cloud Infrastructure

The cloud footprint is small and runs on AWS:

- One EC2 instance in `eu-north-1` (the closest region with consistent capacity for the team's budget).
- One Elastic IP attached to the instance so that DNS records remain stable across reboots.
- One S3 bucket for nightly database backups (`awaqi-backups`, versioning enabled, lifecycle rule: transition to Glacier after 30 days, delete after 365).
- Route 53 is not used; DNS is managed entirely in Cloudflare.

There is no VPC engineering of note. The instance lives in the default VPC's public subnet. All hardening is done at the security-group and Cloudflare layers rather than through private subnets and NAT gateways, because the system has no internal services that need isolation from each other.

### 5.2 Network Configuration

**Security group (production EC2):**

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 443 | TCP | Cloudflare IP ranges (maintained as a managed prefix list) | HTTPS ingress |
| 80 | TCP | Cloudflare IP ranges | HTTP → HTTPS redirect, ACME challenges |
| 22 | TCP | Team static IPs only | SSH |

Ports 5432 (Postgres) and 6379 (Redis) are **not** opened on the security group; both containers bind only to the Docker bridge network. Direct access from outside the host is impossible by design.

**Cloudflare configuration:**

- Proxy mode (orange cloud) on `awaqi.<domain>` and `api.awaqi.<domain>`.
- WAF managed rules enabled (OWASP core ruleset, Cloudflare-managed ruleset).
- Rate-limiting rule on `/api/v1/chat/send` at 30 requests / minute / IP, layered on top of the application-level limit.
- DNSSEC enabled.
- HSTS with a 6-month max-age.

**Nginx (reverse proxy on the host):**

Two server blocks. One serves the web app on `awaqi.<domain>`, proxying to `http://127.0.0.1:3000`. The other serves the API on `api.awaqi.<domain>`, proxying to `http://127.0.0.1:8000`. Both terminate TLS using Certbot-issued Let's Encrypt certificates. Certbot's `--nginx` plugin handles auto-renewal via a daily systemd timer.

No VPN is in place. Operator access is via SSH using key pairs only (password auth disabled in `sshd_config`).

### 5.3 Storage Configuration

- **Persistent storage:** A single 30 GB gp3 EBS volume holds Docker volumes for the Postgres data directory and the document upload directory.
- **Object storage:** S3 (`awaqi-backups`) for database dumps and a copy of every successfully ingested source document. Uploads go through the API's `/admin/documents` endpoint, which writes both to the local volume (for fast extraction) and to S3 (for durable archive).
- **Backup storage:** Nightly `pg_dump --format=custom` runs via cron on the host; the dump is uploaded to `s3://awaqi-backups/postgres/YYYY-MM-DD.dump`. Retention is handled by the S3 lifecycle policy described above. Restore has been tested twice during development — the documented procedure lives in `docs/runbooks/db-restore.md`.

---

## 6. Database Implementation

### 6.1 Database Installation

PostgreSQL 16 is deployed as the `pgvector/pgvector:pg16` Docker image, which ships with the `pgvector` extension preinstalled. The compose service is defined in `docker/docker-compose.db.yml` and mounts a named volume (`awaqi_pgdata`) for persistence. The image's entrypoint runs every SQL file in `docker/init-db/` on first start, which is where `CREATE EXTENSION IF NOT EXISTS vector;` lives.

Redis is the official `redis:7-alpine` image, configured with `--maxmemory 256mb --maxmemory-policy allkeys-lru`. Both services have healthchecks (`pg_isready` and `redis-cli ping`) so that dependent containers wait for them to come up.

Connection strings are read from the `.env` file at the repository root. The API uses the async URL (`postgresql+asyncpg://...`) for SQLAlchemy async, and the Next.js web service uses the sync URL because Better Auth's database driver is synchronous.

### 6.2 Schema Deployment

Schema management goes through Alembic. The migration history is in `packages/database/migrations/versions/` and currently contains 14 migrations. The notable ones:

- `0001_initial_schema` — base tables: `user`, `chat_session`, `message`, `document`.
- `0003_cu_auth_tables` — Better Auth's customer-user tables (separate from admin).
- `0005_phase_a_ingestion` — `document_chunk` table with a `vector(1024)` column for the original e5 embeddings.
- `0009_ba_user_admin_plugin_cols` — Better Auth admin plugin columns (role, banned, banReason).
- `0010_scraper_and_document_registry` — `scraper_run`, `scraped_document` tables for the daily job.
- `0013_gemini_embedding_dim` and `0014_gemini_embedding_3072` — the embedding dimension migration. We initially shipped 1536-d Gemini embeddings (which stay within pgvector's index size limit on older versions) and then migrated to 3072-d after upgrading pgvector to 0.7.x. The `cfc06938f5b2_merge_embedding_dim_heads` revision merges the two heads from a parallel development branch.

Migrations are run by `uv run alembic upgrade head` from the repo root, picking up `DATABASE_URL` from the environment. In production this is part of the API container's entrypoint: the container blocks on a healthy database, runs `alembic upgrade head`, then starts Uvicorn.

**Initial data seeding** is limited to two things:

- The first superadmin user, created by `scripts/seed_superadmin.py`, which reads `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` from the environment and inserts a Better Auth user with the `superadmin` role.
- The default tax taxonomies (Individual / SME / Enterprise) are inserted by the `0001_initial_schema` migration so they are present from the first boot.

There is no synthetic chat or document seed. The knowledge base is built from the scraper and admin uploads.

---

## 7. Backend Implementation

### 7.1 Backend Environment Setup

The backend is a Python 3.12 application managed with `uv`. The repository ships a workspace `pyproject.toml` at the root that pulls together the `api`, `ai-engine`, `database`, `nlu`, and `utils` packages. Running `uv sync --group dev` from the repo root installs everything, including dev tools.

Environment variables are read via Pydantic settings classes (`apps/api/deps.py`, `packages/database/src/database/config.py`). The contract is documented in `.env.example`. The variables that matter most:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async DSN used by FastAPI |
| `DATABASE_URL_SYNC` | Sync DSN used by Next.js (Better Auth) |
| `REDIS_URL` | Rate limiting and session helpers |
| `GOOGLE_API_KEY` | Gemini embeddings + chat |
| `GEMINI_EMBEDDING_MODEL`, `GEMINI_EMBEDDING_DIMENSION` | Override embedding model and dim |
| `BETTER_AUTH_SECRET` | Symmetric secret for Better Auth |
| `SESSION_TOKEN_SECRET` | HMAC key for guest session tokens |
| `TELEGRAM_BOT_TOKEN` | Bot credential |
| `RATE_LIMIT_MAX` | Requests per window (defaults to 15) |
| `RATE_LIMIT_WINDOW_SECONDS` | Window length (defaults to 600) |
| `INGEST_EXTRACTOR` | `gemini` or `native` (PyMuPDF + Tesseract) |

The API entrypoint is `apps/api/main.py`. It wires up CORS, the rate-limit dependency, the routers (`chat`, `admin`, `telegram_link`), the APScheduler-based scraper, and a startup hook that runs Alembic migrations.

### 7.2 API Service Layout

The FastAPI app is organised by concern rather than by entity. The three routers map to the three audiences for the API:

- **`routers/chat.py`** — public chat endpoints used by the web UI and the Telegram bot.
  - `POST /v1/chat/send` — main RAG entry point. Accepts `{ message, session_id?, profile?, language? }`, returns the generated answer with citations, a heuristic confidence score, and a session token (issued on first turn).
  - `GET /v1/chat/history/{session_id}` — session-token-gated history retrieval.
  - `GET /v1/chat/export/{session_id}` — session-token-gated transcript export.
  - `POST /v1/chat/feedback` — record a thumbs-up/down on a message.

- **`routers/admin.py`** — admin operations, gated by Better Auth session validation with `superadmin` or `editor` role.
  - `POST /v1/admin/documents` — upload a regulatory document. The handler stores the file, creates a `Document` row in `pending`, and enqueues the ingestion pipeline.
  - `GET /v1/admin/documents` — list documents with status, stage, and error detail.
  - `POST /v1/admin/documents/{id}/retry` — re-run ingestion for a failed or requires-manual-review document.
  - `POST /v1/admin/documents/{id}/review` — admin-side resolution for `requires_manual_review` items.
  - `GET /v1/admin/health` — system health snapshot (DB, Redis, scheduler, last scraper run).
  - `GET /v1/admin/analytics` — basic counts (sessions, messages, documents by status).
  - `POST /v1/admin/scraper/run` — force a scraper run immediately.

- **`routers/telegram_link.py`** — flow for linking a Telegram chat ID to a registered customer account, so signed-in users can pick up their conversation on the bot.

The "AI service" the SRS imagines lives as the `packages/ai-engine` library rather than as a separate microservice. It is imported by the API directly. This kept the deployment topology simple and avoided an extra network hop on every chat request.

There are **no separate `candidate` or `job` services** — those appear in the requested table of contents but belong to a different project template. Awaqi's service surface is chat + admin + telegram-link.

### 7.3 API Gateway and Cross-Cutting Concerns

Nginx is the gateway in production. Internal to the API process, there are four cross-cutting layers:

1. **CORS** — configured to allow the web origin (`awaqi.<domain>`) and `localhost:3100` for development.
2. **Rate limiting** — `apps/api/deps_rate_limit.py` implements a Redis token bucket keyed by client IP. The default is 15 requests per 600 seconds, matching NFR-15. Limit exceeded returns HTTP 429 with `Retry-After`.
3. **Session token verification** — for guest endpoints that read or export history, the request must carry an HMAC-signed session token issued at session creation. The token binds the session ID to a secret known only to the API, so a guest cannot read someone else's session by guessing UUIDs.
4. **Better Auth session validation** — for admin endpoints, a dependency calls into the web app's Better Auth introspection endpoint to verify the cookie and pull the user's role.

Load balancing is handled at the Nginx layer; we currently run a single API replica because the host has the capacity. Scaling out to multiple replicas requires nothing in the application code — the only shared state is in Postgres and Redis.

---

## 8. Frontend Implementation

### 8.1 Frontend Environment Setup

The web app is Next.js 15 with the App Router and TypeScript in strict mode. Routes live under `apps/web/app/[locale]/...`, with `[locale]` resolved to `en` or `am` by `next-intl` middleware. Tailwind CSS and shadcn/ui supply the design system; component primitives sit in `apps/web/components/ui/`.

Local development uses `npm run dev` and proxies API calls to `http://localhost:8000`. Production builds run inside the `web.Dockerfile` image as a standalone Next.js output, which the container starts with `node server.js` (no Node-server bundling surprises this way).

TypeScript configuration is conventional. Path aliases in `tsconfig.json` allow `@/components/...` and `@/lib/...` imports. ESLint and Prettier run on every PR via the CI Node job.

### 8.2 UI Component Deployment

The user-facing surface has three main areas:

- **Landing page** (`app/[locale]/page.tsx`) — bilingual hero, "start chatting" and "sign in" calls to action.
- **Chat surface** (`app/[locale]/chat/...`) — the main chat experience. Components of note:
  - `ChatWindow` — message list with virtualised rendering for long sessions.
  - `MessageBubble` — renders the assistant message, expandable citations, and the heuristic confidence indicator.
  - `Composer` — input box with language hint and the rate-limit toast.
  - `ProfilePicker` — first-turn modal that asks the guest to pick Individual / SME / Enterprise; the choice is sent with every subsequent message in the session.
- **Admin dashboard** (`app/[locale]/admin/...`) — knowledge base manager (upload, status, retry), scraper controls, analytics, and a logs view. Routes are guarded by middleware that checks the Better Auth session role.

Internationalisation strings live in `apps/web/messages/en.json` and `am.json`. Every user-facing string goes through `useTranslations`; the team's lint rule fails the build if a raw English string is committed in a TSX file outside the messages files.

### 8.3 Frontend Optimisation

Next.js handles most of the optimisation work out of the box: route-level code splitting, image optimisation via `next/image`, font subsetting through `next/font`. On top of that:

- **Build optimisation** — `next build` runs in CI with `NODE_ENV=production`, producing a standalone bundle. The Docker image is multi-stage so the final layer only ships the runtime and the `.next/standalone` output, keeping the image under 200 MB.
- **CDN** — Cloudflare in front of the origin caches static assets (`/_next/static/*`) for a year with `immutable` headers. HTML responses are not cached (every page renders user-aware content).
- **Caching inside the app** — server components fetch admin data with `cache: 'no-store'` because the dashboard needs current state. The chat surface uses SWR for history reads with a five-second `dedupingInterval`.

---

## 9. AI/ML Implementation

### 9.1 AI Environment

There is no dedicated ML runtime. The AI engine is a Python package (`packages/ai-engine`) that the API imports. It depends on:

- `google-genai` for Gemini embeddings and chat
- `pymupdf` and `pytesseract` for document extraction with OCR fallback
- `numpy` and `pgvector`'s Python adapter for vector handling
- `scikit-learn` only for utilities (no model training)

We chose to keep everything inside the API process for two reasons: the heavy lifting (embedding, generation) happens on Gemini's side via HTTPS, so the Python process is mostly I/O-bound; and a separate ML service would add deployment complexity that buys us nothing while we stay on managed APIs.

### 9.2 AI Matching Engine (Retrieval)

The retrieval path lives in `packages/ai-engine/src/ai_engine/hybrid_retrieval.py`. Given a query string, it does the following:

1. **Language detection** — `query_nlu.py` runs a small heuristic that looks at the proportion of Ethiopic Unicode code points to classify the query as `am`, `en`, or `mixed`.
2. **Dense retrieval** — the query is embedded with the configured Gemini embedding model (default `gemini-embedding-001`, 3072-dim in production). The vector is compared against `document_chunk.embedding` using cosine distance (`<=>` in pgvector). The top 50 candidates are returned.
3. **Sparse retrieval** — PostgreSQL FTS over the same chunks (`to_tsvector('simple', content)` with a `tsquery` built from the query). Top 50 candidates by `ts_rank`.
4. **Fusion** — Reciprocal Rank Fusion with `k=60`. Each candidate's RRF score is `sum(1 / (60 + rank_i))` across the two result lists. The top 5 fused candidates go to the generator.

The choice of `simple` as the FTS configuration is deliberate — Postgres's stemmed configurations are tuned for European languages and produced worse results on Amharic than no stemming at all.

### 9.3 Embeddings and Vector Storage

Embeddings come from `gemini-embedding-001` via the Google AI SDK. Documents are chunked into ~1024-token windows with a 100-word overlap, then embedded in batches of 32. The chunk records live in the `document_chunk` table:

```
document_chunk(
  id uuid primary key,
  document_id uuid references document(id) on delete cascade,
  ordinal integer,
  content text,
  content_tsv tsvector generated always as (to_tsvector('simple', content)) stored,
  embedding vector(3072),
  metadata jsonb
)
```

The `embedding` column is indexed with an HNSW index (`vector_cosine_ops`) for fast nearest-neighbour queries. `content_tsv` has a GIN index for FTS.

**Atomic re-index.** When a document is re-ingested, the pipeline opens a transaction, deletes all existing chunks for the document, inserts the new chunks, and commits. The document never enters a state where it has partial chunks visible to retrieval.

### 9.4 Generation and Fallback

`rag_answer.py` builds the prompt: a system message describing the bot's role and citation requirements, the user's question, the user's taxpayer profile if any, and the top 5 retrieved chunks formatted with their source titles and chunk IDs. The Gemini chat model returns the answer, and a post-processing step extracts any citation markers (`[doc:<id>]`) and validates them against the retrieved chunk set. Citations that do not match a retrieved chunk are dropped.

If Gemini is unreachable or returns an error, the pipeline falls back to **extractive synthesis**: it returns the top-ranked chunk's leading sentences, prefixed with a short disclaimer ("Based on retrieved regulation excerpts:"), and includes the source citation. This is deterministic and adds no hallucination risk, but it sacrifices fluency. Operationally it has only fired a handful of times during the project, mostly during Gemini quota incidents.

### 9.5 Confidence Scoring

A heuristic combined score is computed per response using four signals:

- Max cosine similarity from the dense path (weight 0.4)
- Normalised top FTS rank (weight 0.2)
- Citation overlap — share of generated citations that resolve to retrieved chunks (weight 0.3)
- LLM uncertainty proxy from token-level probabilities where available (weight 0.1)

The score is attached to the response payload as `confidence`. The web UI shows it as a coloured chip (green/yellow/red bands). The hard-block gate from the original SRS (no answer below 0.5) is deferred (SRS-DEF-03 / SDS-DEF-04); right now the score is informational rather than a circuit breaker.

---

## 10. Security Implementation

### 10.1 Authentication

Authentication uses **Better Auth** for both admin and customer channels. Better Auth runs inside the Next.js app and exposes its endpoints under `/api/auth/*`. The Python API trusts Better Auth by calling its session-introspection endpoint internally; we do not duplicate password hashing or session storage in Python.

Customer accounts use email + password with mandatory password strength rules and email verification. Admin accounts additionally have a `role` column (`superadmin` or `editor`) handled by Better Auth's admin plugin.

There is no OAuth2 in the current release. Adding Google login is on the backlog (the Better Auth side-config is straightforward) but it was not a requirement for academic acceptance.

JWT is **not** used. The SRS originally specified JWT for the admin channel; during implementation we found Better Auth's cookie-based session model simpler to integrate with Next.js server components and easier to revoke (just delete the row), so the decision was made to use it everywhere. This is captured in SRS-CHG-05 / SDS-CHG-05.

Guest users do not authenticate. They get a UUID session ID at first chat plus an HMAC-signed session token. The token is signed with `SESSION_TOKEN_SECRET` and binds the session ID to a short claim payload. Any subsequent read or export of that session's history requires the token, which the web client stores in `localStorage` and the Telegram bot stores keyed by chat ID.

### 10.2 Authorization

Role-based access control is enforced in two places:

- **Web middleware** (`apps/web/middleware.ts`) — blocks unauthenticated requests to `/admin/*` and redirects to the admin login. Once authenticated, it checks the Better Auth session role and rejects users without `superadmin` or `editor`.
- **API dependency** (`apps/api/deps.py:require_admin`) — every admin router function depends on `require_admin`, which calls Better Auth, fetches the user, and returns the role or raises HTTP 403. Some endpoints further require `superadmin` (e.g., the user-management endpoints).

Permissions are coarse-grained on purpose. The deferred audit-log work (SRS-DEF-04) will eventually make fine-grained per-action permissions worthwhile; while admin actions are not yet immutable-logged, adding more granular roles would add little.

### 10.3 Infrastructure Security

- **WAF** — Cloudflare's managed ruleset, with rule overrides recorded in the Cloudflare config (see `docs/runbooks/cloudflare.md`). The WAF blocks the typical injection and bot patterns before they reach the origin.
- **IDS/IPS** — no in-host IDS is installed. Cloudflare's bot management and the AWS security group are the layered defence; given the small attack surface (two public ports, both terminated at Nginx), a host IDS was deemed disproportionate.
- **Firewall configuration** — see section 5.2. Only Cloudflare IPs and team SSH IPs reach the EC2 instance; everything internal is on the Docker bridge network and not reachable from outside the host.
- **SSH** — key-based only, password auth disabled, root login disabled, `fail2ban` watching `/var/log/auth.log` with a 24-hour ban on 3 failed attempts.

### 10.4 Data Security

- **TLS** — Let's Encrypt certificates from Certbot, renewed by a systemd timer that runs `certbot renew --quiet` daily. Nginx is configured with TLS 1.2/1.3 only, strong ciphers, and OCSP stapling.
- **Encryption at rest** — EBS volume encryption is on with the default AWS KMS key. Postgres column-level encryption is not used because no PII is stored beyond what is needed for session access control (NFR-13).
- **Secrets management** — the `.env` file on the EC2 host owns secrets. It is `chmod 600` to the `awaqi` user and is the only place secrets live unencrypted. CI secrets live in GitHub Actions encrypted secrets. There is no Vault or AWS Secrets Manager integration; the cost was not justified for the current footprint, but the variable contract is small enough that a migration would be a few hours of work.
- **PII handling** — the system explicitly does not request TINs, names, or phone numbers. Chat content is stored, but the privacy wording was updated (SRS-CHG-12) to allow this provided that access is gated by session tokens or Better Auth. Automated PII scrubbing on stored messages is a backlog item.

ClamAV scanning of admin-uploaded documents is planned (SRS-DEF-08, SDS-DEF-01) but not yet active.

---

## 11. DevOps & CI/CD Implementation

### 11.1 Source Control

The repo follows a trunk-based pattern with short-lived feature branches:

- `main` is the deployable branch. Only PRs merge here; direct pushes are blocked.
- Feature branches are named by author and topic (`bas-scraping-data-ingestion`, `aman-fixes`, `telegram_bot`).
- PRs require one approving review and a green CI run. The advisor reviews milestone PRs.
- Commit messages follow a loose conventional style — the recent history shows `ci:`, `fix:`, and `feat:` prefixes; nothing is rigidly enforced.

There is no monorepo tooling layer (no Nx, no Turborepo). The workspace is small enough that `make`, `uv`, and `npm` workspaces cover the cases we need.

### 11.2 CI/CD Pipeline

CI runs in GitHub Actions, defined in `.github/workflows/ci.yml`. The pipeline has three jobs that run on every push to the watched branches and every PR to `main`:

1. **`test-python`** — `uv sync --group dev`, then Ruff lint and unit tests (`tests/api/test_schemas.py`, `tests/api/test_session_token.py`, `tests/packages/`, and the `ai-engine` test suite). Uses fake DB/Redis URLs because these tests do not touch real services.
2. **`test-integration`** — boots an ephemeral `pgvector/pgvector:pg16` service, runs Alembic migrations against it, then runs the integration tests that exercise the chat and admin flows end to end against the real database.
3. **`build-web`** — `npm ci`, lint, type-check, and `next build` inside `apps/web`. Catches type regressions before they reach production.

Deployment is currently a one-line manual step: SSH to the host, `git pull && docker compose -f docker/docker-compose.yml up -d --build`. The migration runs inside the API container's entrypoint, so we do not need a separate `alembic upgrade` step. A GitHub Actions deployment job that SSHs and triggers this is drafted but kept manual for now because the team prefers an explicit go signal during the academic submission window.

Security scanning at the CI level is limited to dependency auditing (`npm audit` advisory report and `uv pip audit` on the Python dependencies). SAST and container scanning are on the backlog.

### 11.3 Containerisation

The compose stack in `docker/docker-compose.yml` defines five services: `api`, `web`, `db`, `redis`, `telegram_bot`. `db` and `redis` are pulled in from `docker-compose.db.yml` and `docker-compose.redis.yml` so that they can also be brought up standalone for local development.

Dockerfiles:

- **`api.Dockerfile`** — Python 3.12 slim base, installs `uv`, copies the workspace, runs `uv sync --package api --no-dev`, and starts Uvicorn after running Alembic migrations.
- **`web.Dockerfile`** — multi-stage. Stage 1 installs all dependencies and runs `next build` with `output: 'standalone'`. Stage 2 is a minimal Node 20 image that copies the standalone output and runs `node server.js`.
- **`bot.Dockerfile`** — same Python base as the API, but the entrypoint runs `python -m telegram_bot`.

Volumes:

- `awaqi_pgdata` — Postgres data directory.
- `awaqi_uploads` — admin document uploads, mounted into the API container.
- Redis is volatile by design.

PM2 supervises the API and web processes inside their containers. The Docker entrypoints invoke `pm2-runtime` rather than the underlying command, which gives PM2 full lifecycle control while keeping the container as the unit of scheduling. PM2 logs are tailed by `docker logs` and surfaced in our incident workflow.

---

## 12. Integration Implementation

The system has fewer third-party integrations than the original SRS scope. The list that landed:

- **Google Gemini API** — embeddings and chat generation. Authenticated by API key, called via the `google-genai` SDK. Errors and rate limits are handled by the AI engine's retry layer (3 attempts with exponential backoff, then extractive fallback).
- **Telegram Bot API** — outbound bot interaction via Pyrogram. The bot logs in with a long-lived bot token and polls for updates; we did not set up webhooks because polling is reliable enough at our message volume and removes the need for a publicly reachable bot endpoint.
- **Ministry of Revenue website (mor.gov.et)** — the scraper, implemented with `httpx` + `BeautifulSoup`, runs once per day at 00:00 EAT under APScheduler. The scraper is in `apps/api/scraper_service.py`; its scheduler is registered at API startup.
- **S3** — boto3 client for backup uploads.
- **Cloudflare** — DNS and WAF only; no API integration in the application code.

Email, SMS, and calendar integrations from the requested table of contents are not part of the system. The product does not have notifications or appointment scheduling.

---

## 13. Monitoring & Logging Implementation

### 13.1 Monitoring

The current production setup leans on PM2 for process supervision and log aggregation. `pm2 monit` and `pm2 status` are the operator's first stop. PM2 is configured to keep the last 7 days of logs rotated daily.

Prometheus and Grafana are scaffolded but not yet enabled in production. The plan:

- Run `prom/prometheus` and `grafana/grafana` as additional compose services on the same host.
- Expose `/metrics` from the FastAPI app (using `prometheus-fastapi-instrumentator`) so we get per-endpoint latency and error rates without extra glue code.
- Add a Postgres exporter and a Redis exporter for resource-level metrics.
- Two starter dashboards: "API health" (request rate, p50/p95 latency, error rate, rate-limited responses) and "Pipeline health" (ingestion status counts, embedding latencies, scraper run history).

This is queued for the post-submission iteration and tracked as a milestone in GitHub Issues.

### 13.2 Logging

Application logs are structured JSON (via `structlog`) written to stdout. Inside the container, PM2 captures them; on the host, `docker logs` streams them out. Nothing currently ships them off-box.

A centralised log stack (ELK or Loki) is part of the same follow-up milestone. The lift to add Loki + Promtail next to Prometheus + Grafana is small; we held off because the project hasn't yet hit the volume where searching across nodes is necessary, given we only run one node.

### 13.3 Alerting

Alerts today are best described as "advisor-grade": the admin dashboard surfaces health information, and the operator checks it. Once Prometheus is in place, alerting goes through Alertmanager with two channels:

- **Slack** — `#awaqi-alerts` for warning-level events (elevated error rate, slow ingestion).
- **Email** — pager email for critical events (API down, scraper has failed three consecutive runs, database disk above 85%).

Incident escalation is a two-step ladder: on-call team member acknowledges in Slack and triages; if unresolved after 30 minutes, the project lead is paged. This is a small team and we expect to grow this discipline rather than over-design it.

---

## 14. Testing Implementation

Testing is split by speed and by what each test needs:

- **Unit tests** (`tests/api/test_schemas.py`, `tests/api/test_session_token.py`, `tests/packages/`, `packages/ai-engine/tests/`) — pure Python, no I/O. Cover Pydantic schemas, HMAC session-token signing, language detection, chunking, RRF scoring, and the deterministic fallback. These run in seconds and gate every PR.
- **Integration tests** — exercise the chat and admin routers against a real Postgres with pgvector. They cover the happy paths (send a message, get a cited response from a stubbed Gemini, retrieve history with the right session token) plus the failure modes (wrong session token returns 403, rate limit fires after 15 requests).
- **Manual UX tests** — driven from a checklist tied to the SRS release-acceptance baseline (section 7 of the SRS). The checklist is in `docs/qa/release-checklist.md` and is run before each milestone demo.
- **Frontend type-check + lint** — covered by `npm run lint` and `npm run build` in CI; treated as the first line of defence for the web app.

What we did not build is an automated evaluation harness for the RAG quality metrics (EM, F1, BERTScore, citation accuracy). The SRS captures this as SRS-DEF-05; the harness will be a separate package that replays a golden set of Q-A pairs and produces a scorecard.

---

## 15. Deployment Procedures

### 15.1 Pre-Deployment Checklist

Before any deployment:

- [ ] CI is green on `main`.
- [ ] Alembic migrations applied locally and reviewed; no migrations are merged that have not been run against a copy of production.
- [ ] `.env.prod` on the host is current with any new variables.
- [ ] Database backup taken in the last 24 hours.
- [ ] Cloudflare maintenance mode is **not** required (only used if we need to push behind-the-scenes work).

### 15.2 Deployment Procedure

1. SSH to the EC2 host as the `awaqi` user.
2. `cd ~/Awaqi && git fetch origin && git checkout main && git pull`.
3. Inspect the diff: `git log --stat HEAD~..HEAD`. Confirm no surprise migrations or env changes.
4. `docker compose -f docker/docker-compose.yml up -d --build`. This rebuilds changed images and rolls them in.
5. Watch the API container's logs for the Alembic migration step and the Uvicorn startup banner.
6. Smoke test:
   - `curl -fsS https://api.awaqi.<domain>/health` returns `{"status":"ok"}`.
   - Open the web app, send a test message in Amharic and one in English, confirm citations render.
   - Telegram: send `/start` to the bot and a test message.
7. Tail the logs for five minutes to catch any startup-induced errors.

### 15.3 Rollback

If a deployment misbehaves:

1. `git log --oneline -10` to find the previous good SHA.
2. `git checkout <prev-sha>`.
3. `docker compose -f docker/docker-compose.yml up -d --build`.
4. If a migration was the cause, restore from the latest `pg_dump` (`docs/runbooks/db-restore.md`) and then redeploy the previous commit. We have rehearsed this twice during development.

---

## 16. Cost Considerations

Approximate monthly run cost at current usage levels:

| Item | Cost |
|---|---|
| EC2 `t3.medium`, on-demand | ~ $30 |
| EBS 30 GB gp3 | ~ $3 |
| Elastic IP (attached) | $0 |
| S3 storage (backups) | < $1 |
| Cloudflare (Free plan) | $0 |
| Domain (yearly, prorated) | ~ $1 |
| Gemini API (embeddings + chat) | Variable; ~ $10–$25 at current traffic |
| **Total** | **~ $45–$60 / month** |

The dominant variable is Gemini API usage. Embedding cost is one-time per document; query-time cost is per chat turn. If usage grows, the first optimisation is to add an embedding cache for frequently repeated queries (e.g., "VAT registration") keyed by normalised query text — this has not been needed yet.

For a production rollout, the cost profile shifts substantially: RDS for Postgres (~$60+/month), ElastiCache for Redis (~$15+/month), and an ALB (~$20/month) make a realistic baseline closer to $150–$200 before Gemini usage.

---

## 17. Implementation Timeline

The project ran from December 2025 through May 2026 in three phases.

### 17.1 Phase 1 — Core Platform (Dec 2025 – Feb 2026)

- Monorepo bootstrap with `uv` and `npm` workspaces.
- Postgres + pgvector + Alembic baseline.
- FastAPI skeleton with `chat/send` returning canned responses.
- Next.js skeleton with the chat surface and Better Auth wired in.
- Docker Compose for the full stack.
- CI on GitHub Actions.

### 17.2 Phase 2 — AI Features (Feb 2026 – Apr 2026)

- Document ingestion pipeline: extraction, OCR fallback, chunking, embeddings.
- Hybrid retrieval: dense + sparse + RRF.
- RAG answer synthesis with citation extraction and validation.
- Extractive fallback path.
- Telegram bot with feature parity for the chat path.
- Daily scraper with APScheduler.
- Admin dashboard: document upload, status, retry, scraper controls.

### 17.3 Phase 3 — Hardening (Apr 2026 – May 2026)

- Embedding dimension migration (1024 → 1536 → 3072) as Gemini and pgvector versions stabilised.
- Better Auth integration polish (admin plugin, role gating).
- Session-token HMAC for guest access.
- Rate limiting tuned to NFR-15 (15 req / 10 min).
- TLS, Cloudflare, security group hardening.
- Documentation: SDS update, SRS update, this document.

Items explicitly carried out of scope into a future iteration: Amharic intent classification, ClamAV scanning, immutable admin audit log, automated RAG-quality evaluation harness, full feedback UX, Prometheus/Grafana monitoring stack, ELK/Loki log aggregation.

---

## 18. Risk and Issue Management

### 18.1 Active Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gemini API outage or quota exhaustion | Medium | High | Extractive fallback returns deterministic answers; quota dashboard reviewed weekly; pluggable embedding/chat backend so the team can swap models without code rewrites |
| MoR website DOM changes break the scraper | Medium | Medium | Scraper is isolated in `scraper_service.py`; admin can disable the schedule and continue serving from the existing corpus; alerts on three consecutive failed runs |
| Single EC2 host = single point of failure | Low (at current scale) | High | Nightly database backups to S3; documented restore procedure; image rebuilds are reproducible from `main` |
| Confidence score gate is informational only | Known | Medium | Citations are mandatory and validated; user-facing disclaimer at chat surface; hard gate is in the backlog as SRS-DEF-03 |
| No malware scanning on admin uploads | Known | Medium | Admin uploads are gated by Better Auth role check; ClamAV integration is the next security ticket |
| Secret management is file-based | Known | Low at current scale | Tight file permissions on `.env.prod`; rotation procedure documented; Vault/Secrets Manager migration is a small follow-up |

### 18.2 Issue Log Process

Issues are tracked in GitHub Issues with labels `bug`, `security`, `infra`, `ai`, `web`, `bot`. The advisor and team triage on the weekly call; severe issues (security or production-down) are handled out-of-band on Telegram and tagged afterwards for traceability. The Linear-style "everything in a tracker" rule keeps the team's status conversations grounded in something other than memory.

---

## 19. References

- SRS v1.1 — `G13_SRS_Final_Updated.docx.txt`
- SDS v1.1 — `G13_SDS_Final_Updated.docx.txt`
- `ARCHITECTURE.md` — top-level technical overview, kept in the repo root
- `Makefile` — canonical list of dev commands
- `.env.example` — environment variable contract
- `docker/docker-compose.yml` — production compose stack
- `.github/workflows/ci.yml` — CI configuration
- FastAPI documentation — https://fastapi.tiangolo.com/
- pgvector — https://github.com/pgvector/pgvector
- Google AI Gemini API — https://ai.google.dev/gemini-api
- Next.js — https://nextjs.org/docs
- Better Auth — https://www.better-auth.com/docs

---

*End of Implementation Documentation, v1.0.*
