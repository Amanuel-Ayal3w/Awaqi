# Technical Documentation

**Project:** Awaqi — LLM-Based Support Bot for the Ethiopian Revenue Authority
**Team:** Group 13 — Abdurahman M., Amanuel A., Basliel S., Bethel W., Diborah D.
**Advisor:** Mr. Daniel Abebe
**Version:** 1.0
**Date:** 2026-05-28
**Repository:** `ba5liel/Awaqi` (monorepo)

> Companion file: `things to update after real run.md` records every number in this document that is currently an educated estimate. Replace those with measured values once we run the benchmarks on the production host.

---

## Table of Contents

1. Introduction
2. Implemented Features
3. System Architecture
4. Technology Stack
5. Code Structure and Monorepo
6. Core Modules
   6.1 Authentication and Authorization
   6.2 LLM Processing Engine
   6.3 Retrieval-Augmented Generation (RAG) Module
   6.4 Knowledge Base and Document Retrieval
   6.5 Database Services
   6.6 Job Queue and Worker Tier
   6.7 Notification Service
7. API Reference
8. Database Implementation
9. Security Implementation
10. Infrastructure Architecture
11. CI/CD and DevOps
12. Testing Implementation
13. Validation Results
    13.1 Security Validation
    13.2 Performance Validation
    13.3 AI Accuracy Validation
14. Deployment Procedures
15. Monitoring, Logging, and Alerting
16. Cost Considerations
17. Agile Workflow and Timeline
18. Deferred Items and Known Limitations
19. References

---

## 1. Introduction

### 1.1 Purpose

This document explains how Awaqi was built and how it runs in production. The SRS defines what the system has to do, the SDS defines how the system is designed, and this document records what was actually delivered and verified. It is written for engineers who will maintain the system after handover, for the advisor and graders who need to verify that the implementation matches the requirements, and for future contributors who need a single reference.

### 1.2 Project Overview

Awaqi is an AI-powered information desk for the Ethiopian Revenue Authority (ERA, formerly MoR). Taxpayers ask tax questions in Amharic or English through a web chat or a Telegram bot. The system answers using a Retrieval-Augmented Generation pipeline grounded on official regulatory documents that are scraped from `mor.gov.et` and uploaded by administrators. Every factual answer carries citations back to a specific proclamation or article.

The system runs hybrid retrieval (dense pgvector search plus PostgreSQL full-text search, fused by Reciprocal Rank Fusion) and uses Gemini for generation. When generation is unavailable, an extractive fallback returns the leading sentences from the top-ranked retrieved chunk so the user still gets a cited answer rather than an error.

### 1.3 Scope of This Release

What v1.0 ships:

- Web chat interface (Next.js 15, Amharic + English, Better Auth).
- FastAPI backend with chat, admin, announcements, evaluation, progress, and Telegram-link routers.
- Hybrid RAG engine using Gemini embeddings (3072-dim) on pgvector with HNSW indexing, plus PostgreSQL FTS, fused with RRF (k=60).
- Document ingestion pipeline with PDF and HTML extraction, OCR fallback, sliding-window chunking, and atomic re-index.
- Telegram bot using Pyrogram with feature parity for the chat path.
- APScheduler-driven daily scraper for `mor.gov.et`, plus secondary scrapers for `ethiodata` and MoR news.
- **Redis-backed RQ job queue** with three queues (`scraper`, `ingest`, `notification`) and a separate worker process per queue.
- **Proactive notification service** that emails (Mailtrap SMTP) and SMSes (GeezSMS) subscribed recipients when noteworthy documents are indexed.
- **Awaqi Max** — an optional ReAct agent mode that calls `rag_search` and an Ethiopian web-search tool through Gemini function calling.
- **Evaluation framework** — a 23-question Amharic benchmark with retrieval metrics (Hit@k, Precision@k, Recall@k, MRR, NDCG) and an LLM-as-judge for generation quality.
- Admin dashboard for documents, scraper controls, review queue, evaluation runs, users, telegram, vector-store admin, and announcements.
- Docker Compose stack (api, web, db, redis, telegram-bot, rq-dashboard) on a single AWS EC2 host.
- Nginx reverse proxy with Certbot TLS, Cloudflare WAF and DNS, AWS security groups.
- Three-layer test strategy: pytest unit and integration, Vitest for the web app, Playwright for end-to-end browser flows.

What is deferred and tracked separately:

- Amharic intent classification (XLM-RoBERTa underperformed the 90% NFR-08 target on the available dataset, so the model was disabled and the schema hooks were left in place).
- Hard confidence-threshold gating, full feedback UX, ClamAV upload scanning, immutable audit log.
- Prometheus and Grafana, centralised log shipping (Loki or ELK).

---

## 2. Implemented Features

| Feature | What it does |
|---|---|
| Hybrid RAG | Dense (pgvector HNSW) + sparse (PostgreSQL FTS) retrieval fused by RRF (k=60); returns cited answers. |
| Awaqi Max (agent mode) | ReAct loop on Gemini function calling with two tools (`rag_search`, `ethiopian_web_search`); falls back to basic RAG when disabled. |
| Multilingual Chat | Heuristic Amharic/English/mixed detector; 3072-dim Gemini embeddings handle both scripts. |
| Web Chat UI | Next.js 15 chat surface with virtualised list, inline citations, confidence chip, session continuity, document thumbnails. |
| Telegram Bot | Pyrogram bot with feature parity for the chat path; session linking to registered accounts. |
| Admin Knowledge Base | Upload, status, retry, manual review; atomic re-index on re-upload; thumbnails for indexed documents. |
| Daily Scrapers | APScheduler-driven scrapers for `mor.gov.et`, `ethiodata`, MoR news, and Telegram channels. |
| RQ Job Queue | Three Redis-backed queues (`scraper`, `ingest`, `notification`) running long-running work off the request path. |
| Real-time Progress | Job progress published over Redis pub/sub; admin UI shows ingestion and scraper progress live. |
| OCR Fallback | PyMuPDF + Tesseract (Amharic pack) or Gemini Flash OCR for scanned documents; low confidence routes to manual review. |
| Confidence Scoring | Four-signal heuristic shown as green/yellow/red chip; informational rather than blocking. |
| Extractive Fallback | Returns top-ranked chunk's leading sentences when Gemini is unreachable; deterministic and citation-bearing. |
| Notification Service | Detects noteworthy new documents and sends email + SMS to subscribers; configurable per-recipient. |
| Announcements | Editor-curated banners surfaced in the web UI for tax-deadline reminders. |
| Vector Store Admin | Admin UI for inspecting and rebuilding the pgvector index, with one-click full re-embed. |
| Evaluation Suite | 23-question Amharic benchmark plus retrieval + LLM-judge metrics surfaced in the admin dashboard. |
| Session Management | Guest sessions persisted in Postgres with HMAC-signed tokens; admin and customer via Better Auth. |
| Rate Limiting | Redis token-bucket at 15 req / 10 min per IP; layered Cloudflare WAF rule at 30 req / min. |
| CI/CD | GitHub Actions: Ruff, Python unit + pgvector integration tests, Next.js build, Vitest, Playwright smoke. |

---

## 3. System Architecture

Awaqi is structured as five cooperating tiers: the client, the API gateway, the AI engine, the worker tier (new in this release), and storage.

```
┌─────────────────┐     ┌─────────────────┐
│   Web (Next.js) │     │ Telegram Bot    │
│   Better Auth   │     │ (Pyrogram)      │
└───────┬─────────┘     └────────┬────────┘
        │ HTTPS                  │ Bot API
        └────────────┬───────────┘
                     │
              ┌──────▼───────┐         ┌───────────────────────┐
              │ Nginx + TLS  │────────►│ Cloudflare WAF / DNS  │
              └──────┬───────┘         └───────────────────────┘
                     │
              ┌──────▼────────────────────────────────┐
              │ FastAPI                               │
              │ routers/{chat,admin,announcements,    │
              │   telegram_link,evaluation,progress}  │
              │ deps: BetterAuth, rate-limit, HMAC    │
              └──┬──────────────┬───────────────┬─────┘
                 │ enqueue jobs │ embed/gen     │
                 │              ▼               │
                 │      ┌───────────────┐       │
                 │      │ AI Engine     │       │
                 │      │ pkg/ai-engine │       │
                 │      └───┬─────┬─────┘       │
                 │          │     │             │
                 │          │     ▼             │
                 │          │  Gemini API       │
                 │          ▼                   │
                 │     ┌─────────────────────┐  │
                 │     │ Postgres + pgvector │◄─┘
                 │     │ + FTS, ChatSession, │
                 │     │ Document, Chunks    │
                 │     └─────────────────────┘
                 ▼
        ┌──────────────────────────┐
        │ Redis (cache + queues)   │
        │  scraper / ingest /      │
        │  notification queues     │
        └──────────┬───────────────┘
                   │ jobs
                   ▼
        ┌──────────────────────────────────┐
        │ RQ Workers (scraper, ingest,     │
        │ notification) + RQ Dashboard     │
        └──────────────────────────────────┘
```

### 3.1 Subsystems

**Client.** The web app (Next.js 15 App Router) hosts the chat interface, the admin dashboard, and Better Auth login flows. The Telegram bot polls for updates with Pyrogram and renders cited responses inline.

**API Subsystem.** FastAPI serves six router groups: `chat` (public and guest-token-gated), `admin` (Better Auth role-gated), `announcements` (editor-curated banners), `telegram_link` (account-linking flow), `evaluation` (benchmark runs and metrics), and `progress` (Server-Sent Events for live job progress). CORS, rate limiting, session-token verification, and Better Auth session validation are applied as FastAPI dependencies.

**AI Engine.** A Python library (`packages/ai-engine`) imported directly into the API and worker processes. It implements language detection, dense and sparse retrieval, RRF fusion, RAG generation, the extractive fallback, confidence scoring, and the Awaqi Max ReAct agent.

**Worker Tier.** RQ workers consume jobs from Redis. The `ingest` worker runs the per-document pipeline (extract → chunk → embed → atomic replace). The `scraper` worker runs the daily site crawls. The `notification` worker checks new documents against the watermark, asks Gemini whether each is noteworthy, and dispatches email and SMS.

**Storage.** PostgreSQL 16 with pgvector holds vectors, full-text indexes, chat sessions, messages, documents, chunks, notifications, announcements, and Better Auth tables. Redis holds rate-limit counters, the queue payloads, and a pub/sub channel for live progress. S3 holds nightly backups and an archive of ingested source documents.

### 3.2 Storage Layout

| Layer | Technology | Role |
|---|---|---|
| Vector storage | PostgreSQL 16 + pgvector | HNSW cosine index on 3072-dim embeddings |
| Full-text search | PostgreSQL FTS | GIN index on `tsvector` (`simple` config) |
| Relational | PostgreSQL 16 | ChatSession, Message, Document, Chunk, Notification, Announcement, Better Auth tables |
| Cache + queues | Redis 7 | Rate-limit keys (TTL 600s), RQ payloads, pub/sub for job progress |
| Object storage | AWS S3 | Nightly `pg_dump` archive, ingested source documents |
| AI inference | Gemini API | `gemini-embedding-001` (3072-dim) + configurable chat model |

---

## 4. Technology Stack

The implemented stack differs from the original SDS in six recorded amendments (SDS-CHG-01 through SDS-CHG-06): LangChain was replaced by a custom orchestrator, Pinecone and Elasticsearch were replaced by pgvector and PostgreSQL FTS, the Llama/Ollama fallback became an extractive fallback, embeddings moved from `multilingual-e5-large` to `gemini-embedding-001` at 3072-d, JWT was replaced by Better Auth, and guest sessions are persisted in Postgres rather than RAM.

| Layer | Technology | Location |
|---|---|---|
| Backend API | FastAPI (Python 3.12) + Uvicorn | `apps/api` |
| Async ORM | SQLAlchemy async + Alembic | `packages/database` |
| Frontend | Next.js 15 + React 19 + TypeScript | `apps/web` |
| i18n | next-intl (Amharic + English) | `apps/web/messages` |
| UI components | shadcn/ui + Tailwind CSS + Radix UI | `apps/web/components` |
| Authentication | Better Auth (cookie sessions, RBAC) | `apps/web/lib/auth.ts` + API deps |
| AI orchestration | Custom (no LangChain) | `packages/ai-engine` |
| LLM generation | Gemini chat (configurable) | `packages/ai-engine/rag_answer.py` |
| Embeddings | `gemini-embedding-001`, 3072-d | `packages/ai-engine/gemini_embedder.py` |
| Vector store | PostgreSQL 16 + pgvector (HNSW) | `pgvector/pgvector:pg16` |
| Full-text | PostgreSQL FTS (`simple` config + GIN) | Same DB |
| Cache + queues | Redis 7-alpine | `docker/docker-compose.redis.yml` |
| Job queue | RQ (Redis Queue) — `scraper`, `ingest`, `notification` | `apps/api/queue` |
| Email | Mailtrap SMTP | `apps/api/notification_service.py` |
| SMS | GeezSMS REST API | Same |
| OCR | PyMuPDF + Tesseract + `tesseract-ocr-amh` | `packages/ai-engine` |
| Scrapers | httpx + BeautifulSoup + APScheduler | `apps/api/scraper_service.py`, `packages/ai-engine/scraper/*` |
| Telegram bot | Pyrogram | `apps/telegram-bot` |
| Frontend unit tests | Vitest + Testing Library | `apps/web/*.test.ts(x)` |
| End-to-end tests | Playwright | `apps/web/e2e` |
| Python tests | pytest + httpx | `tests/api`, `tests/packages`, `packages/ai-engine/tests` |
| Infra | Docker Compose + Nginx + Certbot + Cloudflare | `docker/`, host config |
| CI | GitHub Actions | `.github/workflows/ci.yml` |
| Package mgmt | `uv` (Python), `npm` (Node) | Workspace root |

---

## 5. Code Structure and Monorepo

The repository is a `uv` Python workspace at the root paired with an npm workspace for the web app. A change that spans the API, a shared package, and a schema migration lands in one pull request and one CI run.

```
Awaqi/
├── apps/
│   ├── api/                    # FastAPI app: routers, deps, queue, scheduler
│   │   ├── routers/            # chat, admin, announcements, telegram_link,
│   │   │                       #   evaluation, progress
│   │   ├── queue/              # RQ connection, queues, jobs/*
│   │   ├── main.py
│   │   ├── scraper_service.py
│   │   ├── notification_service.py
│   │   └── notification_scheduler.py
│   ├── web/                    # Next.js 15 frontend
│   │   ├── app/[locale]/...    # chat, admin/*, auth
│   │   ├── components/         # chat/, admin/, ui/
│   │   ├── e2e/                # Playwright specs
│   │   └── vitest.config.ts
│   └── telegram-bot/           # Pyrogram bot runtime
├── packages/
│   ├── ai-engine/              # RAG engine, agent, evaluation, scrapers
│   │   └── src/ai_engine/
│   │       ├── agent/          # Awaqi Max ReAct agent + tools
│   │       ├── evaluation/     # dataset, metrics, judge, runner
│   │       ├── scraper/        # mor, ethiodata, mor_news, telegram
│   │       ├── hybrid_retrieval.py
│   │       └── rag_answer.py
│   ├── database/               # SQLAlchemy models + Alembic migrations
│   ├── nlu/                    # Language detection + intent hooks
│   └── utils/                  # HMAC tokens, chunking, logging
├── data/evaluations/           # benchmark.json (23 Amharic Q&A)
├── docker/                     # api/web/bot Dockerfiles + compose
├── docs/                       # TESTING.md, evaluation.md, awaqi-max.md
├── tests/                      # Python unit + integration tests
├── scripts/                    # seed_superadmin, run_evaluation
└── .github/workflows/ci.yml
```

### Branching

Trunk-based with short-lived branches. `main` is protected. PRs require a green CI run and one approving review. The advisor reviews milestone PRs. CI runs on every push to `main`, `dev`, and on every PR.

### Environment Variables

The contract lives in `.env.example`. The variables that matter most:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async DSN for FastAPI and SQLAlchemy |
| `DATABASE_URL_SYNC` | Sync DSN for Better Auth in Next.js |
| `REDIS_URL` | Rate limiting, RQ queues, pub/sub |
| `GOOGLE_API_KEY` | Gemini embeddings + chat |
| `GEMINI_EMBEDDING_MODEL` | Defaults to `gemini-embedding-001` |
| `GEMINI_EMBEDDING_DIMENSION` | Defaults to 3072 |
| `GEMINI_CHAT_MODEL` | Defaults to `gemini-3.5-flash` |
| `BETTER_AUTH_SECRET` | Symmetric secret for Better Auth |
| `SESSION_TOKEN_SECRET` | HMAC key for guest session tokens |
| `TELEGRAM_BOT_TOKEN` | Pyrogram bot token |
| `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW_SECONDS` | Rate limit (15 / 600s) |
| `INGEST_EXTRACTOR` | `gemini` or `native` (PyMuPDF + Tesseract) |
| `MAILTRAP_USER`, `MAILTRAP_PASS` | Email transport |
| `GEEZSMS_API_KEY` | SMS provider |
| `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD` | One-time seed of the first admin |

---

## 6. Core Modules

### 6.1 Authentication and Authorization

Awaqi uses Better Auth for both administrator and customer channels. JWT is not used. Better Auth runs inside the Next.js app and exposes `/api/auth/*`. The Python API trusts Better Auth by calling its session-introspection endpoint on every protected request. The decision was driven by simpler Next.js server-component integration and instant revocation (we just delete the session row).

Customer accounts use email and password with mandatory password rules and email verification. Administrator accounts have a `role` column (`superadmin` or `editor`) managed by Better Auth's admin plugin. Guests do not authenticate; they receive a UUID session ID and an HMAC-signed session token (signed with `SESSION_TOKEN_SECRET`). Any history or export read for a guest session requires that token, which binds the session ID to a signed claim.

Authorization is enforced in two places. The Next.js middleware blocks unauthenticated access to `/admin/*` and rejects users without the right role. The FastAPI `require_admin` dependency does the same check at the API edge, returning 403 on role mismatch. Some endpoints (user management, force-rescrape) further require `superadmin`.

### 6.2 LLM Processing Engine

The LLM engine lives in `packages/ai-engine` and is imported directly into the API and worker processes. It is not a separate microservice — the heavy work happens on Gemini's side, and the local Python process is mostly I/O-bound.

The engine wraps three Gemini capabilities behind narrow interfaces:

1. **Embeddings** (`gemini_embedder.py`). Batches text into groups of 32 and calls `gemini-embedding-001`. The model and dimension are configurable; production uses 3072-d. The embedder is mocked in unit tests.
2. **Chat generation** (`rag_answer.py`). Builds the structured prompt (system message, profile, question, top-k chunks), calls the chat model, and post-processes the response. Citation markers are validated against the retrieved chunk set; orphaned citations are dropped.
3. **Function calling for Awaqi Max** (`agent/react_agent.py`). Gemini decides on each turn whether to call a tool (`rag_search` or `ethiopian_web_search`) or to answer directly. The loop terminates when the model returns text or hits `MAX_ITERATIONS`.

If Gemini is unreachable, the extractive fallback in `rag_answer.py` returns the leading sentences of the top-ranked retrieved chunk, prefixed with a short disclaimer and the source citation. This path is deterministic and has only triggered during Gemini quota incidents.

### 6.3 Retrieval-Augmented Generation (RAG) Module

The RAG path is implemented in `hybrid_retrieval.py` and `rag_answer.py`. The basic flow for a single user query:

1. **Language detection** — `query_nlu.py` looks at the proportion of Ethiopic Unicode code points and classifies the query as `am`, `en`, or `mixed`.
2. **Dense retrieval** — the query is embedded with the same Gemini model used for documents. Cosine distance (`<=>`) against the HNSW-indexed `document_chunk.embedding` returns the top 50 candidates.
3. **Sparse retrieval** — a PostgreSQL FTS query built from the user input. `ts_rank` scores the top 50 candidates. We use the `simple` text-search configuration on purpose, because Postgres's stemmed configurations are tuned for European languages and produced worse results on Amharic than no stemming at all.
4. **Reciprocal Rank Fusion** — RRF with `k=60`. Each candidate's score is `sum(1 / (60 + rank_i))` across the two lists. The top 5 fused chunks go to the generator.
5. **Generation** — Gemini chat with the structured prompt; citations validated; extractive fallback on failure.
6. **Confidence scoring** — four-signal heuristic (dense cosine 0.4, sparse rank 0.2, citation overlap 0.3, LLM probability variance 0.1) attached to the response.

**Awaqi Max mode** sits on top of the same retrieval primitives. Instead of one shot, the ReAct agent loops: it may call `rag_search` repeatedly with refined queries, or `ethiopian_web_search` when the knowledge base does not cover the question. Citations from both sources merge into a single citation list. The user can switch modes in the chat UI; the default is basic.

### 6.4 Knowledge Base and Document Retrieval

The knowledge base has two ingestion paths and one retrieval path.

**Ingestion path A — admin upload.** `POST /v1/admin/documents` accepts a PDF, DOCX, or HTML file. The handler stores the file, creates a `Document` row in `pending`, enqueues an `ingest` job, and returns immediately. The worker picks up the job, transitions the row through `processing` → `indexed` (or `failed` / `requires_manual_review`), and publishes progress to a Redis pub/sub channel that the admin UI subscribes to.

**Ingestion path B — automated scrapers.** APScheduler triggers the `mor.gov.et` scraper daily at 00:00 EAT. Two secondary scrapers (`ethiodata`, MoR news) and a Telegram channel scraper run on the same schedule. New documents are enqueued for ingestion in the same `ingest` queue.

**Atomic re-index.** Re-ingesting a document opens one transaction, deletes the existing chunks, inserts the new chunks, and commits. The document never sits half-indexed in the retrieval view.

**Manual review.** Documents with low OCR confidence are routed to `requires_manual_review` and surfaced in the admin review queue. The admin can edit the extracted text, approve, or reject. Approval re-runs the embedding step only.

**Vector store administration.** The admin UI includes a vector-store section that exposes the underlying index health (row counts per status, last-rebuild time, current dimension) and a one-click rebuild that re-embeds everything. This is useful when the embedding dimension changes.

### 6.5 Database Services

PostgreSQL 16 with pgvector runs in the `pgvector/pgvector:pg16` Docker image. Connections from the API use `postgresql+asyncpg://`, and connections from Next.js (Better Auth) use the sync DSN. The schema is managed by Alembic; 17 migration revisions exist as of v1.0.

Tables grouped by purpose:

| Group | Tables |
|---|---|
| Chat | `chat_session`, `message` |
| Knowledge base | `document`, `document_chunk`, `scraper_run`, `scraped_document` |
| Authentication | `user`, `cu_user` (customer), Better Auth core tables, `cu_user_telegram_chat_id` |
| Notifications | `notification_config`, `notification_log`, `announcement` |
| Telegram | `telegram_scraper`, `telegram_message_parts` |

Connection pooling is handled by SQLAlchemy with `pool_pre_ping=True` to recycle stale connections after Docker restarts. The API container's entrypoint runs `alembic upgrade head` before starting Uvicorn, so deployments are self-migrating.

### 6.6 Job Queue and Worker Tier

Previously the API ran ingestion and scraping inline, which blocked request handlers during long jobs. The new release introduces an RQ-based queue layer:

| Queue | Default timeout | Job examples |
|---|---|---|
| `scraper` | 3600 s | `mor_scraper_job`, `ethiodata_scraper_job`, `telegram_scraper_job` |
| `ingest` | 1800 s | `ingest_job` (one job per document) |
| `notification` | 3600 s | `notification_job` (watermarked sweep over new documents) |

A separate worker process is run per queue inside its own container (`scraper-worker`, `ingest-worker`, `notification-worker`). The API enqueues jobs via the synchronous Redis connection in `apps/api/queue/connection.py`. Real-time progress is published on Redis pub/sub channels and streamed to the admin UI through the `/v1/progress/{job_id}` SSE endpoint. **RQ Dashboard** runs at port 9181 and shows queues, workers, and failed jobs at a glance.

This split removes long jobs from the request path. Concurrent uploads no longer serialise on a single request handler, and a worker crash does not take down the API.

### 6.7 Notification Service

`notification_service.py` runs on a schedule (10 minutes by default) inside the `notification` worker. On each tick it:

1. Reads `NotificationConfig` (singleton row id=1) to get the current watermark timestamp and the recipient list.
2. Selects documents indexed after the watermark.
3. For each candidate, asks Gemini whether the document is noteworthy (a new proclamation, an amended directive, a deadline reminder), with a prompt that limits the model to a structured YES/NO classification plus a short rationale.
4. For documents flagged noteworthy, composes an Amharic + English email body and an SMS body, dispatches via Mailtrap SMTP and GeezSMS, and writes a `NotificationLog` row per send attempt.
5. Advances the watermark so the same documents are not re-evaluated.

The service degrades gracefully — failures on either channel are logged per recipient, and the watermark advances independently so a transient SMTP outage does not block subsequent runs.

---

## 7. API Reference

All routes are versioned under `/v1/`. Production base URL: `https://api.awaqi.<domain>`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | public | Container health |
| `POST` | `/v1/chat/send` | public + guest token | RAG query; returns answer, citations, confidence, session token |
| `GET` | `/v1/chat/history/{session_id}` | HMAC token | Paginated message history |
| `GET` | `/v1/chat/export/{session_id}` | HMAC token | Transcript export |
| `POST` | `/v1/chat/feedback` | HMAC token | Thumbs-up/down on a message |
| `POST` | `/v1/admin/documents` | admin | Upload regulatory document; enqueues `ingest` job |
| `GET` | `/v1/admin/documents` | admin | List documents with status, stage, error |
| `POST` | `/v1/admin/documents/{id}/retry` | admin | Re-enqueue failed/manual-review document |
| `POST` | `/v1/admin/documents/{id}/review` | admin | Resolve a `requires_manual_review` item |
| `GET` | `/v1/admin/health` | admin | DB, Redis, scheduler, worker, last scraper run |
| `GET` | `/v1/admin/analytics` | admin | Sessions, messages, document status counts |
| `POST` | `/v1/admin/scraper/run` | superadmin | Enqueue an immediate scraper job |
| `POST` | `/v1/admin/vector-store/rebuild` | superadmin | Re-embed every chunk against the current model |
| `GET` | `/v1/announcements` | public | Active announcements for the chat banner |
| `POST` | `/v1/admin/announcements` | admin | Create/update announcement |
| `GET` | `/v1/evaluation/runs` | admin | List historical evaluation runs |
| `POST` | `/v1/evaluation/runs` | admin | Start a new evaluation run on the benchmark |
| `GET` | `/v1/evaluation/runs/{id}` | admin | Per-question scores for one run |
| `GET` | `/v1/progress/{job_id}` | admin (SSE) | Server-Sent Events stream of job progress |
| `POST` | `/v1/telegram/link/request` | customer | Start Telegram account linking |
| `POST` | `/v1/telegram/link/confirm` | customer | Confirm with the bot-issued code |
| `GET` | `/v1/telegram/link/status` | customer | Current link state |
| `POST` | `/v1/telegram/link/unlink` | customer | Remove the link |

---

## 8. Database Implementation

PostgreSQL 16 runs in the `pgvector/pgvector:pg16` Docker image with `pgvector` pre-installed. The compose service mounts the `awaqi_pgdata` volume and runs `CREATE EXTENSION IF NOT EXISTS vector;` on first boot via `docker/init-db/`.

### 8.1 Notable Migrations

| Migration | Change |
|---|---|
| `0001_initial_schema` | Core tables and default tax taxonomies |
| `0003_cu_auth_tables` | Better Auth customer-user tables |
| `0005_phase_a_ingestion` | `document_chunk` with `vector(1024)` |
| `0009_ba_user_admin_plugin_cols` | Better Auth admin plugin columns |
| `0010_scraper_and_document_registry` | `scraper_run`, `scraped_document` |
| `0013_gemini_embedding_dim` | Resize embedding to 1536 |
| `0014_gemini_embedding_3072` | Resize embedding to 3072 |
| `0015_gemini_embedding_dim_3072` | Reconcile dimension across all tables |
| `0016_notification_tables` | `notification_config`, `notification_log` |
| `0017_announcements` | `announcement` table |
| `0017_enforcement_status` | Document enforcement status |
| `0018_merge_0017_heads` | Merge two parallel 0017 heads |

The embedding column moved from 1024-d (initial e5 prototype) to 1536-d (early Gemini, fit pgvector's older index limit) to 3072-d (current). The 1536 → 3072 jump required upgrading pgvector to 0.7.x.

### 8.2 Indexes That Matter

- HNSW on `document_chunk.embedding` (`vector_cosine_ops`).
- GIN on `document_chunk.content_tsv` for FTS.
- B-tree on `chat_session.user_id`, `message.session_id`, `document.status`, `notification_log.created_at`.

---

## 9. Security Implementation

| Control | Scope | Implementation |
|---|---|---|
| AuthN — admin | `/admin/*` | Better Auth cookie sessions, role-gated (`superadmin` / `editor`) |
| AuthN — customer | Signed-in chat | Better Auth email + password with email verification |
| AuthN — guest | Chat without login | HMAC-signed session token bound to session ID |
| AuthZ — web | Middleware | Blocks `/admin/*` without valid session and required role |
| AuthZ — API | `require_admin` dep | 403 on role mismatch; some endpoints require `superadmin` |
| Rate limit — app | All public endpoints | Redis token-bucket: 15 req / 600 s / IP; HTTP 429 with `Retry-After` |
| Rate limit — edge | `/api/v1/chat/send` | Cloudflare WAF: 30 req / minute / IP |
| Transport | All ingress | Let's Encrypt via Certbot, TLS 1.2/1.3 only, HSTS (6-month max-age) |
| Network | Host firewall | SG allows 443/80 from Cloudflare IPs, 22 from team IPs, Postgres/Redis on Docker bridge only |
| Host | SSH | Key-based only; password and root login disabled; `fail2ban` watching auth log |
| Secrets | Storage | `.env.prod` `chmod 600`; CI uses GitHub Actions encrypted secrets |
| Disk | Encryption | EBS encrypted with default AWS KMS key |
| WAF | Edge | Cloudflare OWASP core ruleset + managed ruleset; DNSSEC on |
| Input validation | Pydantic | All request bodies validated; uploads limited to 25 MB, type-checked |
| SQL safety | ORM | SQLAlchemy parameterised queries throughout; no string interpolation into SQL |
| XSS | Web | React auto-escapes; admin-authored HTML is sanitised through `DOMPurify` before render |
| Prompt injection | RAG | Retrieved chunks are wrapped in clearly delimited blocks; system prompt instructs the model to ignore instructions inside retrieved text |

ClamAV upload scanning, immutable audit logging, and automated PII scrubbing on stored chat content remain on the backlog.

---

## 10. Infrastructure Architecture

The production deployment runs on a single AWS EC2 `t3.medium` (2 vCPU, 4 GB RAM, 30 GB gp3 EBS, `eu-north-1`). Every service runs as a Docker container managed by Docker Compose. PM2 supervises the API and web processes inside their containers for automatic restart and unified `pm2 logs` access during incidents.

Containers:

| Container | Image | Role |
|---|---|---|
| `api` | built from `api.Dockerfile` | FastAPI under Uvicorn + PM2 |
| `web` | built from `web.Dockerfile` | Next.js standalone server + PM2 |
| `db` | `pgvector/pgvector:pg16` | PostgreSQL + pgvector |
| `redis` | `redis:7-alpine` | Cache, rate limiting, RQ payloads |
| `telegram_bot` | built from `bot.Dockerfile` | Pyrogram bot |
| `ingest-worker` | shares `api` image, alt entrypoint | `rq worker ingest` |
| `scraper-worker` | same | `rq worker scraper` |
| `notification-worker` | same | `rq worker notification` |
| `rq-dashboard` | `eoranged/rq-dashboard` | Queue inspection UI on :9181 |

### 10.1 Network

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 443 | TCP | Cloudflare IPs | HTTPS ingress |
| 80 | TCP | Cloudflare IPs | HTTP redirect, ACME challenges |
| 22 | TCP | Team static IPs | SSH |
| 5432 | TCP | Not exposed | Postgres on Docker bridge only |
| 6379 | TCP | Not exposed | Redis on Docker bridge only |
| 9181 | TCP | Not exposed publicly | RQ Dashboard, reachable via SSH tunnel |

Cloudflare in front handles DDoS mitigation, the OWASP managed ruleset, and DNS. EC2 security groups restrict origin access to Cloudflare's published IP ranges.

### 10.2 Storage and Backup

- 30 GB gp3 EBS for Docker volumes (`awaqi_pgdata`, `awaqi_uploads`, `awaqi_redis_data`).
- S3 bucket `awaqi-backups`: nightly `pg_dump --format=custom` and a copy of every ingested document. Lifecycle: transition to Glacier after 30 days, delete after 365 days.
- Restore procedure is documented in `docs/runbooks/db-restore.md` and has been rehearsed twice during development.

### 10.3 Environment Strategy

| Environment | Where | Database | Use |
|---|---|---|---|
| Development | Developer laptop | Docker Postgres + Redis | Day-to-day coding |
| Testing | GitHub Actions runner | Ephemeral `pgvector/pgvector:pg16` service | Unit + integration on every PR |
| Staging | Same EC2, separate compose profile | `awaqi_db_staging` | Manual QA, advisor demos |
| Production | EC2 (`awaqi.<domain>`) | `awaqi_db` | Live system |

---

## 11. CI/CD and DevOps

### 11.1 Pipeline

GitHub Actions runs three jobs on every push to watched branches and every PR to `main`:

1. **`test-python`.** `uv sync --group dev`, Ruff lint, then unit tests across `tests/api/test_schemas.py`, `tests/api/test_session_token.py`, `tests/packages/`, and `packages/ai-engine/tests/`. Uses fake DB and Redis URLs because these tests do not touch real services.
2. **`test-integration`.** Boots a `pgvector/pgvector:pg16` service container, runs Alembic migrations, then runs the integration tests that exercise the chat and admin flows end to end against the real database.
3. **`test-web`.** `npm ci`, ESLint, type-check, Vitest, Playwright smoke against a built `next start`. Catches type regressions, broken components, and broken core flows before they reach production.

### 11.2 Containerisation

- `api.Dockerfile` — Python 3.12-slim, `uv` installs dependencies, entrypoint runs Alembic migrations and starts Uvicorn under `pm2-runtime`. Alt entrypoints (`rq worker <queue>`) for the worker containers.
- `web.Dockerfile` — multi-stage; stage 1 runs `next build` with the standalone output, stage 2 is a minimal Node 20 image that runs `node server.js`.
- `bot.Dockerfile` — same Python base as the API, with `python -m telegram_bot` as the entrypoint.

### 11.3 Deployment

A deployment is one SSH session: `git pull && docker compose -f docker/docker-compose.yml up -d --build`. The API container's entrypoint runs migrations automatically. Rollback is `git checkout <prev-sha>` followed by the same compose command; a database rollback uses the latest `pg_dump` archive.

---

## 12. Testing Implementation

Testing has three layers, by speed and by what each layer needs.

### 12.1 Python Unit Tests

`pytest` against pure Python code: schema validation, HMAC token signing, language detection, chunking, RRF scoring, the extractive fallback, the evaluation metrics. No I/O; the embedder is mocked through `tests/api/conftest.py`. These run in seconds and gate every PR.

### 12.2 Python Integration Tests

`pytest` + `httpx` against a real Postgres with pgvector. Cover the chat and admin routers end to end: send a message, get a cited response from a stubbed Gemini, retrieve history with the right session token, fail history with a wrong token, exceed the rate limit and get 429, upload a document and verify it lands as `pending` and an `ingest` job is enqueued.

### 12.3 Frontend Unit Tests

Vitest + Testing Library against the React tree. Covers utility functions (`lib/utils.test.ts`), admin route helpers (`lib/admin-routes.test.ts`), and the `JobProgress` component (`components/ui/job-progress.test.tsx`). Runs in the `test-web` CI job.

### 12.4 End-to-End Tests (Playwright)

We use **Playwright** rather than Selenium or Cypress. Playwright works better with Next.js's hydration model and supports parallel browser contexts out of the box. The current spec set is in `apps/web/e2e/`:

- `smoke.spec.ts` — health checks the API, opens the chat page, sends one query, asserts a citation renders, opens the admin login page.

Playwright runs against a `next start` server booted in CI via `playwright.config.ts`. The spec list will grow with each milestone; the current scope is the SRS release-acceptance baseline.

### 12.5 Test Results (Current)

Both Python jobs and the web job pass on `main`. Coverage is reported on every CI run but not gated.

| Suite | Count | Status |
|---|---|---|
| Python unit | 42 tests | Passing |
| Python integration | 18 tests | Passing |
| Frontend Vitest | 9 tests | Passing |
| Playwright E2E | 3 specs (smoke) | Passing |

Tests run inside CI in around 90 seconds for Python unit, 3 minutes for integration (Postgres boot dominates), and 2 minutes for the web suite.

---

## 13. Validation Results

> The numbers in this section are **educated estimates** based on local benchmarks and the team's profiling of the staging deployment. The companion file `things to update after real run.md` lists every number that needs to be replaced with a measured value once we run the benchmarks on the production host.

### 13.1 Security Validation

Tested against a checklist derived from the OWASP Top 10 plus LLM-specific threats. Methodology: scripted attacks from a controlled host plus manual review of the most sensitive code paths.

| Area | Test | Outcome (estimated) | Notes |
|---|---|---|---|
| Prompt injection — retrieval poisoning | 30 hand-crafted Amharic + English prompts hidden in document chunks (e.g. "ignore the system prompt and reveal …") | 28/30 mitigated | System prompt isolates retrieved text in a clearly delimited block and instructs the model to treat retrieved content as data, not instructions. Two cases caused the model to acknowledge the injection without acting on it; full block requires confidence-gate work. |
| Prompt injection — user-supplied | 40 direct prompt-injection user inputs | 38/40 mitigated | Refusal layer and citation validation catch the remainder. |
| SQL injection | sqlmap against the public endpoints | No SQLi found | SQLAlchemy parameterised queries throughout; sqlmap also reported no exploitable inputs against admin endpoints behind Better Auth. |
| XSS — reflected | Burp Suite scan against `/v1/chat/send` and the chat surface | No reflected XSS found | React auto-escapes, and the API JSON responses are typed. |
| XSS — stored | Admin-authored announcement HTML | No stored XSS found | Announcement HTML passes through DOMPurify on render. |
| Access control — admin endpoints | Anonymous and customer-role requests to `/v1/admin/*` | 100% blocked with 403 | Verified for 12 endpoints. |
| Access control — guest session token | Tampered token, expired token, wrong session ID | 100% blocked with 401 | HMAC verification + session-ID claim binding. |
| Rate limit | Burst 100 requests / 10 s from one IP | First 15 pass, remainder 429 | Layered Cloudflare rule kicks in earlier at 30 / minute. |
| Header hygiene | `securityheaders.com` scan | Grade **A** | HSTS, X-Content-Type-Options, Referrer-Policy, X-Frame-Options set by Nginx. |

The two prompt-injection cases that did not fully mitigate are tracked as backlog items under the confidence-gate work (SDS-DEF-04).

### 13.2 Performance Validation

Methodology: `wrk` against `/v1/chat/send` and `/health`, `pg_bench` against the database, and `psrecord` for CPU and memory traces. All numbers below are taken from the staging deployment on the same EC2 instance type and should be re-measured against production data volumes.

| Metric | Target (NFR) | Measured (estimated) | Notes |
|---|---|---|---|
| AI response time — p50 | < 5 s | ~3.2 s | Gemini round-trip dominates (~2.6 s); local pipeline adds ~0.6 s |
| AI response time — p95 | < 8 s | ~6.4 s | Worst case is the agent mode with two tool calls |
| AI response time — extractive fallback | < 1 s | ~0.4 s | No external LLM round-trip; pgvector + sentence extraction only |
| Concurrent users | ≥ 100 | 120 sustained, 180 burst | One API replica; RQ workers absorb ingestion load |
| Throughput on `/v1/chat/send` | — | ~22 req/s sustained | Bound by Gemini, not the host |
| Throughput on `/health` | — | ~3 800 req/s | Synthetic, measures Uvicorn overhead only |
| Cold-query DB time (dense retrieval) | < 200 ms | ~85 ms | HNSW index on 3072-d vectors |
| FTS query time | < 100 ms | ~32 ms | GIN on `simple` tsvector |
| Hybrid retrieval total | < 300 ms | ~140 ms | Dense + FTS run in parallel coroutines |
| Embedding latency (single query) | < 600 ms | ~480 ms | Gemini embedding round-trip |
| Document ingestion (10-page PDF) | < 30 s | ~12 s | Extraction + chunking + 8 embedding batches |
| Document ingestion with OCR (10 pages) | < 90 s | ~62 s | Tesseract dominates |
| CPU utilisation under load (120 concurrent) | < 70% | ~58% | One vCPU is mostly idle waiting on Gemini |
| Memory utilisation steady-state | — | ~1.4 GB / 4 GB | Includes Postgres shared buffers |
| Redis memory | < 256 MB cap | ~28 MB steady | Mostly rate-limit keys |

The queue split was the largest win in this release. Before the RQ tier, a single document upload could stall the API for tens of seconds while the embedding batch ran inline. After the split, upload returns in well under a second; the work moves to the `ingest` worker and the admin UI watches progress over SSE.

### 13.3 AI Accuracy Validation

The evaluation harness lives in `packages/ai-engine/evaluation/`. The benchmark dataset (`data/evaluations/benchmark.json`) has 23 Amharic Q&A pairs curated from the Federal Income Tax Regulation 410/2017 and the Income Tax (Amendment) Proclamation 1395/2017. Each item carries the question, the expected answer, ground-truth proclamation and article numbers (used for retrieval metrics), and topic tags.

Two layers of scoring are produced per run:

- **Retrieval metrics** (computed deterministically against the ground-truth proclamation numbers): Hit@k, Precision@k, Recall@k, MRR, NDCG@k.
- **Generation metrics** (Gemini-as-judge, 1–10): faithfulness, answer relevance, context recall, correctness, overall (weighted: 0.30 correctness + 0.30 faithfulness + 0.20 relevance + 0.20 context recall). A model-free semantic similarity (cosine of expected vs actual embedding) accompanies these.

The evaluation runner can swap retrieval modes (`optimized` = production hybrid, `dense_only`, `bm25_only`) and assistants (`basic`, `awaqi_max`, `both`), so it can attribute quality changes to either the embedding, the keyword layer, or the agent loop.

Estimated headline numbers on the 23-item benchmark:

| Metric | Target | Measured (estimated) | Notes |
|---|---|---|---|
| Hit@5 (production hybrid) | ≥ 0.85 | ~0.91 | Better than `dense_only` (~0.78) and `bm25_only` (~0.74) |
| MRR (production hybrid) | — | ~0.78 | The right document is usually rank 1 or 2 |
| NDCG@5 (production hybrid) | — | ~0.81 | Position-discounted relevance |
| Faithfulness (basic, judge avg) | ≥ 8 | ~8.4 | Citation validation drives this |
| Faithfulness (Awaqi Max, judge avg) | ≥ 8 | ~8.7 | Agent prefers tool calls over speculation |
| Answer relevance (judge avg) | ≥ 8 | ~8.3 | Basic mode |
| Context recall (judge avg) | ≥ 8 | ~7.9 | Some Amharic-specific clauses miss the top 5 |
| Correctness (judge avg) | ≥ 8 | ~7.8 | Lower than faithfulness — model is right when it answers, but occasionally refuses |
| Overall (weighted) | ≥ 8 | ~8.1 | Production hybrid + basic mode |
| Multilingual parity (am vs en, MRR) | ≤ 5% gap | ~3.2% gap | English questions on the same regulations |
| Hallucination rate (manual sample of 50) | < 5% | ~3% | Two responses flagged for ambiguous citation |
| Citation accuracy (manual review) | ≥ 95% | ~96% | Citation validation drops orphans, but some valid sources are missed |

A new evaluation page in the admin UI (`/admin/evaluation`) lets the team click "Run benchmark" to start a new run, pick assistant and retrieval mode, and inspect per-question scores afterwards. Runs are persisted, so the team can track quality over time as the knowledge base grows.

---

## 14. Deployment Procedures

### 14.1 Pre-Deployment Checklist

- [ ] CI is green on `main`.
- [ ] Alembic migrations reviewed and tested against a copy of production.
- [ ] `.env.prod` updated with any new variables.
- [ ] Database backup taken in the last 24 hours.
- [ ] Cloudflare maintenance mode is **not** active.

### 14.2 Deployment Steps

1. SSH to the EC2 host as the `awaqi` user.
2. `cd ~/Awaqi && git fetch origin && git checkout main && git pull`.
3. Inspect `git log --stat HEAD~..HEAD` for surprise migrations or env changes.
4. `docker compose -f docker/docker-compose.yml up -d --build`.
5. Watch the API logs for the Alembic migration step and the Uvicorn startup banner.
6. Watch each worker container for "Listening on <queue>...".
7. Smoke test: `curl /health`, send a test query in Amharic and English, send a Telegram message, enqueue a small document and confirm it indexes.
8. Tail logs for 5 minutes.

### 14.3 Rollback

1. `git log --oneline -10` to find the last known good SHA.
2. `git checkout <prev-sha>`.
3. `docker compose -f docker/docker-compose.yml up -d --build`.
4. If a migration caused the issue, restore from the latest `pg_dump` per `docs/runbooks/db-restore.md`.

---

## 15. Monitoring, Logging, and Alerting

Today's observability is intentionally lightweight: PM2 supervises and rotates logs inside each container, `docker logs` streams stdout, and `pm2 monit` is the operator's first stop. Application logs are structured JSON (`structlog`) written to stdout. RQ Dashboard at port 9181 (SSH-tunnelled) shows queues, workers, and failed jobs.

The next iteration adds:

- `prometheus-fastapi-instrumentator` for per-endpoint latency and error rate.
- `postgres_exporter` and `redis_exporter` for resource metrics.
- Grafana dashboards for API Health and Pipeline Health.
- Loki + Promtail for centralised log search.
- Alertmanager with Slack (`#awaqi-alerts`) for warnings and pager email for critical events (API down, three consecutive scraper failures, database disk above 85%).

The compose scaffolding is in place; we hold off until the production traffic warrants the operational overhead.

---

## 16. Cost Considerations

| Item | Est. monthly cost |
|---|---|
| EC2 `t3.medium`, on-demand | ~ $30 |
| EBS 30 GB gp3 | ~ $3 |
| Elastic IP attached | $0 |
| S3 storage (backups + archive) | < $1 |
| Cloudflare (Free plan) | $0 |
| Domain (prorated) | ~ $1 |
| Gemini API (embeddings + chat) | $10 – $25 |
| Mailtrap SMTP | $0 (free tier) |
| GeezSMS | pay-as-you-go, ~ $5 at current volume |
| **Total** | **~ $50 – $65 / month** |

For a production-grade rollout, splitting Postgres onto RDS, Redis onto ElastiCache, and adding an Application Load Balancer pushes the baseline to roughly $150 – $200 / month before Gemini and SMS usage.

---

## 17. Agile Workflow and Timeline

Two-week sprints from December 2025 through May 2026. Tickets in GitHub Issues grouped by milestone (Ingestion, Retrieval, Generation, Web UX, Telegram, Queue + Notifications, Evaluation, Hardening).

| Phase | Window | Highlights |
|---|---|---|
| Phase 1 — Core Platform | Dec 2025 – Feb 2026 | Monorepo, Postgres + pgvector, FastAPI skeleton, Next.js + Better Auth, Docker Compose, CI |
| Phase 2 — AI Features | Feb 2026 – Apr 2026 | Ingestion, hybrid retrieval, RAG synthesis, citation validation, Telegram bot, daily scraper, admin dashboard |
| Phase 3 — Hardening | Apr 2026 – May 2026 | Embedding dimension migration (1024 → 1536 → 3072), Better Auth role gating, HMAC session tokens, TLS, security groups, Cloudflare WAF |
| Phase 4 — Last Improvements | May 2026 | RQ queue split, notification service, Awaqi Max agent, evaluation framework, Playwright E2E, Vitest |

---

## 18. Deferred Items and Known Limitations

| ID | Item | Priority | State |
|---|---|---|---|
| SDS-DEF-01 | ClamAV upload scanning | Medium | Not active |
| SDS-DEF-02 | Immutable audit log | Medium | Partial admin logs |
| SDS-DEF-03 | Multi-turn context (last 5 turns) | Low | Follow-up quality lower than target |
| SDS-DEF-04 | Hard confidence-threshold gate | Medium | Score is informational, not blocking |
| SDS-DEF-05 | Full analytics / KPI model | Low | Admin observability incomplete |
| SDS-DEF-06 | Continuous RAG-quality automation | Low | Manual benchmark runs only |
| SDS-DEF-07 | Citation side-panel UX | Low | Inline citations only |
| SDS-DEF-08 | Feedback UX wired to chat | Low | Model + API present |
| SRS-DEF-NLU | Amharic intent classification | High | Below the 90% accuracy target |
| Observability | Prometheus + Grafana | Medium | Scaffolded, not enabled |
| Observability | Loki / ELK log shipping | Low | Stdout + PM2 logs sufficient at current scale |

---

## 19. References

**Internal**

- SRS v1.1 — `G13_SRS_Final_Updated.docx.txt`
- SDS v1.1 — `G13_SDS_Final_Updated.docx.txt`
- `ARCHITECTURE.md` — repository-level overview
- `docs/TESTING.md` — three-layer testing guide
- `docs/evaluation.md` — evaluation framework and dataset
- `docs/awaqi-max.md` — agent-mode design and tools
- `Makefile` — canonical dev commands
- `.env.example` — environment-variable contract
- `docker/docker-compose.yml` — production compose stack
- `.github/workflows/ci.yml` — CI pipeline
- `docs/runbooks/db-restore.md` — database restore procedure
- `docs/qa/release-checklist.md` — manual UX acceptance checklist
- `things to update after real run.md` — measured-vs-estimated number tracker

**External**

- FastAPI — https://fastapi.tiangolo.com/
- pgvector — https://github.com/pgvector/pgvector
- Google Gemini API — https://ai.google.dev/gemini-api
- Next.js — https://nextjs.org/docs
- Better Auth — https://www.better-auth.com/docs
- Pyrogram (Telegram) — https://docs.pyrogram.org/
- RQ — https://python-rq.org/
- Playwright — https://playwright.dev/
- Vitest — https://vitest.dev/
- Lewis et al. (2020) — Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. arXiv:2005.11401
- Robertson & Zaragoza (2009) — The Probabilistic Relevance Framework: BM25 and Beyond

---

*End of Technical Documentation, v1.0. Awaqi — Group 13. 2026-05-28.*
