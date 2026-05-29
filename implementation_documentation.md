# Implementation Documentation

**Project:** Awaqi — LLM-Based Support Bot for the Ethiopian Revenue Authority
**Team:** Group 13 — Abdurahman M., Amanuel A., Basliel S., Bethel W., Diborah D.
**Advisor:** Mr. Daniel Abebe
**Institution:** Addis Ababa University, College of Technology and Built Environment, School of IT and Engineering, Department of IT/SE
**Version:** 1.1
**Date:** 2026-05-28
**Repository:** `ba5liel/Awaqi` (monorepo)
**Companion file:** `things to update after real run.md` — placeholder values for the metrics we will measure on the production deployment.

---

## Table of Contents

1. Introduction
2. Implemented Features (Mapped to Requirements)
3. System Architecture
4. Technology Stack
5. Folder Structure
6. How We Implemented Each Module
   6.1 Authentication and Authorization
   6.2 LLM Processing Engine
   6.3 Retrieval-Augmented Generation (RAG) Module
   6.4 Knowledge Base and Document Retrieval
   6.5 Database Services
   6.6 Job Queue and Worker Tier (new in v1.1)
   6.7 Notification Service (new in v1.1)
   6.8 Awaqi Max — Agent Mode (new in v1.1)
   6.9 Evaluation Framework (new in v1.1)
7. API Reference
8. Database Implementation
9. Security Implementation
10. Infrastructure and Deployment
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

This document records how the team implemented the requirements in the SRS and the design choices in the SDS. The SRS says what the system has to do, the SDS says how it is designed, and this document says what was actually built — file by file, decision by decision, and number by number.

It is written for three audiences: engineers who will maintain the system after handover, the advisor and graders verifying that the build matches the requirements, and future contributors who need a single grounded reference.

### 1.2 Project Overview

Awaqi is an AI-powered information desk for the Ethiopian Revenue Authority (ERA, formerly MoR). Taxpayers ask tax questions in Amharic or English through a web chat or a Telegram bot. The system answers using a Retrieval-Augmented Generation pipeline grounded on official regulatory documents that are scraped from `mor.gov.et` and uploaded by administrators. Every factual answer carries citations back to a specific proclamation or article.

Hybrid retrieval (dense pgvector search plus PostgreSQL full-text search, fused with Reciprocal Rank Fusion) feeds a Gemini chat model for generation. When generation is unavailable, an extractive fallback returns the leading sentences from the top-ranked retrieved chunk so the user still gets a cited answer rather than an error.

### 1.3 What Changed Between v1.0 and v1.1 of This Document

v1.0 covered the core platform and the original RAG pipeline. v1.1 adds the work delivered in the May 28 release:

- A **Redis-backed RQ job queue** with three queues (`scraper`, `ingest`, `notification`) and a dedicated worker container per queue.
- A **proactive notification service** that emails (Mailtrap SMTP) and SMSes (GeezSMS) subscribed recipients when noteworthy new documents are indexed.
- **Awaqi Max**, an optional ReAct agent mode built on Gemini function calling with two tools (`rag_search`, `ethiopian_web_search`).
- An **evaluation framework** with a 23-question Amharic benchmark, retrieval metrics, and an LLM-as-judge for generation quality, surfaced in a new `/admin/evaluation` page.
- Secondary scrapers for `ethiodata` and MoR news, plus expanded Telegram scraping.
- Live job progress over Redis pub/sub, streamed to the admin UI via Server-Sent Events.
- A **vector-store admin** section that lets the admin inspect and rebuild the pgvector index.
- A frontend test layer (**Vitest** for components and utilities) and a real end-to-end layer (**Playwright** smoke specs).
- An **announcements** module — editor-curated banners shown above the chat.
- Document thumbnails for indexed PDFs.

### 1.4 Scope

In scope for v1.1:

- Web chat interface (Next.js 15, Amharic + English, Better Auth).
- FastAPI backend with chat, admin, announcements, evaluation, progress, and Telegram-link routers.
- Hybrid RAG engine using Gemini embeddings (3072-d) on pgvector + PostgreSQL FTS + RRF.
- Document ingestion pipeline with PDF/HTML extraction, OCR fallback, sliding-window chunking, atomic re-index.
- Telegram bot (Pyrogram) with feature parity for the chat path.
- APScheduler-driven daily scrapers (`mor.gov.et`, `ethiodata`, MoR news, Telegram channels).
- RQ-based worker tier for long-running jobs.
- Proactive notification service (email + SMS).
- Awaqi Max agent mode.
- Evaluation framework and admin UI.
- Three-layer test strategy (pytest unit/integration, Vitest, Playwright).
- Docker Compose stack on a single EC2 host with Nginx + Certbot TLS + Cloudflare WAF/DNS.

Excluded from this release (documented in §18):

- Amharic intent and entity classification — initial XLM-RoBERTa experiments underperformed the 90% NFR-08 target on the available dataset, so the model was disabled and the schema hooks were left in place.
- Hard confidence-threshold gating, full feedback UX, ClamAV scanning, immutable audit log, Prometheus + Grafana, and centralised log shipping (Loki / ELK).

---

## 2. Implemented Features (Mapped to Requirements)

The table below ties each delivered feature back to the requirement that drove it.

| Feature | Implements | Implementation Location |
|---|---|---|
| Hybrid RAG (dense + sparse + RRF) | FR-06, NFR-04 | `packages/ai-engine/src/ai_engine/hybrid_retrieval.py` |
| Multilingual chat (Am + En) | FR-04, NFR-18 | `packages/ai-engine/src/ai_engine/query_nlu.py` + `apps/web/messages/` |
| RAG answer with citations | FR-07, FR-09, NFR-06 | `packages/ai-engine/src/ai_engine/rag_answer.py` |
| Confidence scoring (4-signal heuristic) | FR-08, NFR-07 | `rag_answer.py` (score block) |
| Extractive fallback | SDS-CHG-03 | `rag_answer.py:_extractive_fallback` |
| Web chat interface | UI-01..05 | `apps/web/app/[locale]/(chat-app)/*` |
| Admin dashboard | FR-23..28 | `apps/web/app/[locale]/(admin)/admin/*` |
| Document upload + atomic re-index | UC-03 | `apps/api/routers/admin.py` + `packages/ai-engine/src/ai_engine/ingest.py` |
| Daily MoR scraper | UC-02, FR-01 | `apps/api/scraper_service.py` + `packages/ai-engine/src/ai_engine/scraper/mor_scraper.py` |
| Ethiodata + MoR-news + Telegram scrapers | FR-01 (extended) | `packages/ai-engine/src/ai_engine/scraper/*` |
| Telegram bot | FR-Telegram | `apps/telegram-bot/src/telegram_bot/` |
| Better Auth (admin + customer) | NFR-16, SRS-CHG-05 | `apps/web/lib/auth.ts` + `apps/api/deps.py` |
| HMAC guest session token | SRS-CHG-04 | `packages/utils/src/utils/session_token.py` |
| Redis rate limiting (15 req / 10 min) | NFR-15 | `apps/api/deps_rate_limit.py` |
| RQ job queue (scraper / ingest / notification) | NFR-09, NFR-10 | `apps/api/queue/*` |
| Live job progress (SSE) | UI ingestion status | `apps/api/routers/progress.py` + `apps/api/queue/progress.py` |
| Notification service (email + SMS) | new in v1.1 | `apps/api/notification_service.py` + `notification_scheduler.py` |
| Announcements module | new in v1.1 | `apps/api/routers/announcements.py` |
| Awaqi Max (ReAct agent) | new in v1.1 | `packages/ai-engine/src/ai_engine/agent/*` |
| Evaluation framework | NFR-22, SDS-DEF-06 partial | `packages/ai-engine/src/ai_engine/evaluation/*` + `data/evaluations/` |
| Document thumbnails | UX | `packages/ai-engine/src/ai_engine/thumbnail.py` + `apps/web/components/ui/doc-thumbnail.tsx` |
| Vector store admin (rebuild) | maintenance | `packages/database/src/database/vector_store_admin.py` |
| Three-layer tests (pytest, Vitest, Playwright) | NFR-20 | `tests/`, `apps/web/**/*.test.ts(x)`, `apps/web/e2e/` |

---

## 3. System Architecture

The implementation follows the four-subsystem decomposition in the SDS, with a fifth tier (the **worker tier**) added in v1.1 to move long-running jobs off the request path.

```
┌──────────────────────┐        ┌──────────────────────┐
│  Web (Next.js 15)    │        │  Telegram Bot        │
│  Better Auth         │        │  (Pyrogram)          │
└──────────┬───────────┘        └──────────┬───────────┘
           │ HTTPS                         │ Bot API
           └──────────────┬────────────────┘
                          │
                  ┌───────▼────────┐     ┌─────────────────────────┐
                  │  Nginx + TLS   │◄────│ Cloudflare WAF / DNS    │
                  └───────┬────────┘     └─────────────────────────┘
                          │
              ┌───────────▼────────────────────────────┐
              │  FastAPI (apps/api)                    │
              │  routers/{chat, admin, announcements,  │
              │   telegram_link, evaluation, progress} │
              │  deps: BetterAuth · rate-limit · HMAC  │
              └─┬──────────────┬──────────────────┬────┘
                │ enqueue      │ embed / generate │
                │              ▼                  │
                │     ┌──────────────────┐        │
                │     │ AI Engine        │        │
                │     │ packages/        │        │
                │     │  ai-engine       │        │
                │     └────┬─────┬───────┘        │
                │          │     │                │
                │          │     ▼                │
                │          │  Gemini API          │
                │          ▼                      │
                │   ┌──────────────────────────┐  │
                │   │ Postgres + pgvector + FTS│◄─┘
                │   └──────────────────────────┘
                ▼
        ┌──────────────────────────────────────┐
        │ Redis (cache · queues · pub/sub)     │
        │  rate limits · scraper · ingest ·    │
        │  notification queues                 │
        └────────────────┬─────────────────────┘
                         │ jobs
                         ▼
        ┌──────────────────────────────────────┐
        │ RQ Workers                           │
        │  scraper · ingest · notification     │
        │  + RQ Dashboard (:9181)              │
        └──────────────────────────────────────┘
```

### 3.1 Subsystems

**Client.** The web app (Next.js 15 App Router) hosts the chat surface, the admin dashboard, and Better Auth login flows. The Telegram bot polls for updates with Pyrogram and renders cited responses inline.

**API.** FastAPI serves six router groups. CORS, rate limiting, session-token verification, and Better Auth session validation are FastAPI dependencies applied per router.

**AI Engine.** A Python library (`packages/ai-engine`) imported directly into the API and worker processes. It runs language detection, hybrid retrieval, RRF fusion, RAG generation, the extractive fallback, the confidence scorer, and the Awaqi Max agent. Calls to Gemini for embeddings and chat are wrapped in narrow interfaces.

**Worker Tier (new).** RQ workers consume jobs from Redis. The `ingest` worker runs the per-document pipeline. The `scraper` worker runs the daily site crawls. The `notification` worker scans new documents and dispatches email and SMS.

**Storage.** PostgreSQL 16 with pgvector holds vectors, full-text indexes, chat sessions, messages, documents, chunks, notifications, announcements, and Better Auth tables. Redis holds rate-limit counters, queue payloads, and a pub/sub channel for live progress. S3 holds nightly backups and an archive of ingested documents.

### 3.2 Storage Layout

| Layer | Technology | Role |
|---|---|---|
| Vectors | PostgreSQL 16 + pgvector | HNSW cosine index on 3072-d embeddings |
| FTS | PostgreSQL FTS | GIN index on `tsvector` (`simple` config) |
| Relational | PostgreSQL 16 | ChatSession, Message, Document, Chunk, Notification, Announcement, Better Auth |
| Cache + queues | Redis 7 | Rate-limit keys, RQ payloads, pub/sub |
| Object storage | AWS S3 | `pg_dump` backups, ingested document archive |
| AI inference | Gemini API | `gemini-embedding-001` + configurable chat model |

---

## 4. Technology Stack

The stack differs from the original SDS in six recorded amendments (SDS-CHG-01..06):

| Layer | Technology | Notes |
|---|---|---|
| Backend API | FastAPI (Python 3.12) + Uvicorn | Replaces Nest.js reference (SDS-CHG-01) |
| Async ORM | SQLAlchemy async + Alembic | |
| Frontend | Next.js 15 + React 19 + TypeScript | App Router |
| i18n | next-intl (Amharic + English) | |
| UI components | shadcn/ui + Tailwind CSS + Radix UI | |
| Authentication | Better Auth (cookie sessions, RBAC) | Replaces JWT (SDS-CHG-05) |
| AI orchestration | Custom (packages/ai-engine) | No LangChain (SDS-CHG-01) |
| LLM generation | Gemini chat (configurable) | |
| Embeddings | `gemini-embedding-001`, 3072-d | Replaces multilingual-e5-large (SDS-CHG-02) |
| Vector store | PostgreSQL 16 + pgvector | Replaces Pinecone (SDS-CHG-06) |
| Full-text | PostgreSQL FTS (`simple` + GIN) | Replaces Elasticsearch (SDS-CHG-06) |
| Cache | Redis 7-alpine | |
| Job queue | RQ (Redis Queue) | New in v1.1 |
| Email | Mailtrap SMTP | New in v1.1 |
| SMS | GeezSMS REST API | New in v1.1 |
| OCR | PyMuPDF + Tesseract + `tesseract-ocr-amh` | |
| Scrapers | httpx + BeautifulSoup + APScheduler | |
| Telegram bot | Pyrogram | |
| Frontend unit tests | Vitest + Testing Library | New in v1.1 |
| End-to-end tests | Playwright | New in v1.1 (Selenium/Cypress not used; see §12) |
| Python tests | pytest + httpx | |
| Infra | Docker Compose + Nginx + Certbot + Cloudflare | |
| CI | GitHub Actions | |
| Package mgmt | `uv` (Python), `npm` (Node) | Workspace at repo root |

---

## 5. Folder Structure

The repository is a single monorepo. A `uv` workspace at the root manages the Python packages, and an npm workspace manages the web app. The layout is intentionally flat: every app lives in `apps/` and every shared library lives in `packages/`.

```
Awaqi/
│
├── apps/                                    # Runnable applications
│   ├── api/                                 # FastAPI backend
│   │   ├── routers/                         # HTTP route groups
│   │   │   ├── chat.py                      # Public + guest-gated chat
│   │   │   ├── admin.py                     # Admin (Better Auth gated)
│   │   │   ├── announcements.py             # Editor-curated banners
│   │   │   ├── telegram_link.py             # Account linking flow
│   │   │   ├── evaluation.py                # Benchmark runs and metrics
│   │   │   └── progress.py                  # SSE job-progress stream
│   │   ├── queue/                           # RQ wiring (new in v1.1)
│   │   │   ├── connection.py                # Sync Redis pool for RQ
│   │   │   ├── queues.py                    # scraper / ingest / notification
│   │   │   ├── progress.py                  # Pub/sub helpers
│   │   │   └── jobs/                        # Job entrypoints
│   │   │       ├── ingest_job.py
│   │   │       ├── mor_scraper_job.py
│   │   │       ├── telegram_job.py
│   │   │       └── notification_job.py
│   │   ├── deps.py                          # FastAPI dependencies (auth)
│   │   ├── deps_rate_limit.py               # Redis token-bucket
│   │   ├── main.py                          # ASGI app factory
│   │   ├── schemas.py                       # Pydantic models
│   │   ├── scraper_service.py               # APScheduler wiring
│   │   ├── scraper_scheduler.py             # Cron-style triggers
│   │   ├── telegram_service.py              # Bot bridge
│   │   ├── telegram_scheduler.py            # Telegram crawl scheduler
│   │   ├── notification_service.py          # Email/SMS dispatcher
│   │   ├── notification_scheduler.py        # Notification tick
│   │   └── document_preview.py              # Thumbnail endpoints
│   │
│   ├── web/                                 # Next.js 15 frontend
│   │   ├── app/[locale]/                    # App Router (Amharic + English)
│   │   │   ├── (admin)/admin/               # Admin section
│   │   │   │   ├── documents/
│   │   │   │   ├── knowledge-base/
│   │   │   │   ├── review-queue/
│   │   │   │   ├── scraper/
│   │   │   │   ├── evaluation/              # New in v1.1
│   │   │   │   ├── settings/
│   │   │   │   ├── telegram/
│   │   │   │   └── users/
│   │   │   ├── (chat-app)/                  # Main chat UX
│   │   │   ├── (chat-auth)/                 # Customer login/signup
│   │   │   ├── login/                       # Admin login
│   │   │   └── signup/
│   │   ├── app/api/                         # Better Auth + Next API routes
│   │   ├── components/
│   │   │   ├── admin/                       # Sidebar, dashboards
│   │   │   ├── auth/                        # Forms
│   │   │   ├── chat/                        # ChatInput, ChatInterface
│   │   │   ├── landing/
│   │   │   ├── layout/                      # Header, footer
│   │   │   ├── settings/
│   │   │   └── ui/                          # shadcn primitives + custom
│   │   │       ├── doc-thumbnail.tsx        # New in v1.1
│   │   │       ├── job-progress.tsx         # SSE consumer (new in v1.1)
│   │   │       └── notification-bell.tsx    # New in v1.1
│   │   ├── e2e/                             # Playwright specs (new in v1.1)
│   │   │   └── smoke.spec.ts
│   │   ├── hooks/                           # React hooks
│   │   ├── i18n/                            # next-intl config
│   │   ├── lib/                             # API client, helpers
│   │   ├── messages/                        # en.json, am.json
│   │   ├── middleware.ts                    # Route gating
│   │   ├── playwright.config.ts             # New in v1.1
│   │   ├── vitest.config.ts                 # New in v1.1
│   │   └── vitest.setup.ts
│   │
│   └── telegram-bot/                        # Pyrogram bot runtime
│       └── src/telegram_bot/
│
├── packages/                                # Shared libraries
│   ├── ai-engine/                           # RAG engine
│   │   └── src/ai_engine/
│   │       ├── agent/                       # Awaqi Max (new in v1.1)
│   │       │   ├── react_agent.py
│   │       │   └── tools.py
│   │       ├── evaluation/                  # Benchmark runner (new in v1.1)
│   │       │   ├── dataset.py
│   │       │   ├── judge.py
│   │       │   ├── metrics.py
│   │       │   └── runner.py
│   │       ├── scraper/                     # Site scrapers
│   │       │   ├── mor_scraper.py
│   │       │   ├── mor_news_scraper.py      # New in v1.1
│   │       │   ├── ethiodata_scraper.py     # New in v1.1
│   │       │   ├── telegram_scraper.py
│   │       │   └── telegram_parse.py
│   │       ├── chunker.py                   # Sliding-window chunking
│   │       ├── chunking_service.py
│   │       ├── document_processor.py
│   │       ├── extractor.py                 # PDF/HTML + OCR
│   │       ├── gemini_embedder.py           # Embedding wrapper
│   │       ├── e5_embedder.py               # Legacy embedder
│   │       ├── hybrid_retrieval.py          # Dense + sparse + RRF
│   │       ├── query_nlu.py                 # Language detection
│   │       ├── rag_answer.py                # Generation + fallback + scoring
│   │       ├── safety.py                    # Refusal / profanity
│   │       ├── text_quality.py              # OCR confidence + cleaning
│   │       ├── thumbnail.py                 # Doc thumbnail rendering (new)
│   │       └── ingest.py                    # End-to-end ingestion entrypoint
│   │
│   ├── database/                            # SQLAlchemy models + migrations
│   │   ├── migrations/versions/             # Alembic revisions (18 files)
│   │   └── src/database/
│   │       ├── models/
│   │       │   ├── document.py
│   │       │   ├── chat.py
│   │       │   ├── user.py
│   │       │   ├── notification.py          # New in v1.1
│   │       │   └── announcement.py          # New in v1.1
│   │       ├── db.py                        # Async engine + session factory
│   │       ├── redis_client.py
│   │       └── vector_store_admin.py        # Rebuild helpers (new in v1.1)
│   │
│   ├── nlu/                                 # Language detection + intent hooks
│   │   └── src/nlu/
│   │
│   └── utils/                               # Shared helpers
│       └── src/utils/                       # HMAC token, chunking, logging
│
├── data/
│   └── evaluations/
│       └── benchmark.json                   # 23 Amharic Q&A (new in v1.1)
│
├── docker/
│   ├── api.Dockerfile
│   ├── web.Dockerfile
│   ├── bot.Dockerfile
│   ├── docker-compose.yml                   # Full stack
│   ├── docker-compose.db.yml                # Postgres-only overlay
│   ├── docker-compose.redis.yml             # Redis + RQ Dashboard overlay
│   └── init-db/                             # CREATE EXTENSION vector;
│
├── docs/
│   ├── TESTING.md                           # Three-layer test guide (new)
│   ├── evaluation.md                        # Benchmark explanation (new)
│   ├── awaqi-max.md                         # Agent-mode design (new)
│   └── runbooks/                            # db-restore.md, cloudflare.md
│
├── kb/
│   └── evaluaiton-question-and-answer       # Source for benchmark.json
│
├── scripts/
│   ├── seed_superadmin.py                   # Bootstrap first admin
│   ├── run_evaluation.py                    # CLI evaluation runner (new)
│   └── telegram_gen_session.py
│
├── tests/
│   ├── api/                                 # FastAPI integration tests
│   │   ├── conftest.py                      # client, admin_session fixtures
│   │   ├── test_schemas.py
│   │   ├── test_session_token.py
│   │   └── test_admin_extra.py              # New in v1.1
│   └── packages/                            # Shared-package unit tests
│
├── .github/workflows/
│   └── ci.yml                               # Python + integration + web jobs
│
├── AGENTS.md
├── ARCHITECTURE.md                          # Top-level technical overview
├── Makefile                                 # make check, dev, test
├── README.md
├── pyproject.toml                           # uv workspace root
├── uv.lock
└── .env.example                             # Environment-variable contract
```

A few rules the team follows when adding files:

- New routes go under an existing `routers/<group>.py` unless they justify a new group.
- New shared logic goes into a package, not into `apps/api`. The rule of thumb: if both the API and a worker need it, it belongs in `packages/`.
- Migrations are numbered sequentially. Two parallel heads (`0017_*` and `0017_*`) get reconciled by a merge revision (`0018_merge_*`).
- Tests sit next to the code in the web app (`*.test.ts(x)` co-located) and centrally for Python (`tests/api/`, `tests/packages/`).

---

## 6. How We Implemented Each Module

This section explains the as-built shape of each major module, the requirement it satisfies, and the file paths a reviewer would open first.

### 6.1 Authentication and Authorization

**Requirements:** NFR-13..16, UC-03 preconditions, SRS-CHG-05.

We use **Better Auth** for both admin and customer channels. Better Auth runs inside the Next.js app at `apps/web/lib/auth.ts` and exposes its endpoints under `/api/auth/*`. The Python API trusts Better Auth by calling its session-introspection endpoint on every protected request.

Two facts drove the choice over JWT:

1. Server-side sessions integrate naturally with Next.js server components, so the admin pages can render without a separate "fetch user" round-trip on every navigation.
2. Sessions are instantly revocable by deleting the row, which we needed for the "ban admin" flow.

Customer accounts use email + password with mandatory password rules and email verification. Admin accounts have a `role` column (`superadmin` / `editor`) managed by Better Auth's admin plugin.

Guest users do not authenticate. They get a UUID session ID and an HMAC-signed session token (signed with `SESSION_TOKEN_SECRET`). The token binds the session ID to a signed claim, so a guest cannot read someone else's session by guessing UUIDs. Token signing and verification live in `packages/utils/src/utils/session_token.py`.

Authorization is enforced in two places:

- `apps/web/middleware.ts` blocks unauthenticated access to `/admin/*` and rejects users without the right role.
- `apps/api/deps.py:require_admin` does the same check at the API edge. Some endpoints (force-rescrape, user management, vector-store rebuild) further require `superadmin`.

### 6.2 LLM Processing Engine

**Requirements:** FR-07, FR-08, FR-09, NFR-04..07.

The LLM engine lives in `packages/ai-engine` and is imported directly into the API and worker processes. It is not a separate microservice because the heavy work happens on Gemini's side and the local Python process is mostly I/O-bound.

The engine wraps three Gemini capabilities behind narrow interfaces:

1. **Embeddings** (`gemini_embedder.py`). Batches text into groups of 32 and calls `gemini-embedding-001`. The model and dimension are configurable; production uses 3072-d. The embedder is auto-mocked in unit tests.
2. **Chat generation** (`rag_answer.py`). Builds the structured prompt (system message, taxpayer profile, question, top-k chunks), calls the chat model, and post-processes the response. Citation markers like `[doc:<id>]` are validated against the retrieved chunk set; orphaned citations are dropped before the response goes out.
3. **Function calling for Awaqi Max** (`agent/react_agent.py`). Gemini decides each turn whether to call `rag_search` or `ethiopian_web_search`, or to answer directly. The loop terminates when the model returns text or hits `MAX_ITERATIONS`.

If Gemini fails, the extractive fallback in `rag_answer.py` returns the leading sentences of the top-ranked retrieved chunk, prefixed with a short disclaimer and the source citation. This path is deterministic and adds no hallucination risk; it has only fired during Gemini quota incidents.

### 6.3 Retrieval-Augmented Generation (RAG) Module

**Requirements:** FR-06, FR-07, NFR-04, NFR-19.

For one user query, the pipeline runs as follows. The code-path entry point is `rag_answer.answer()`.

1. **Language detection** — `query_nlu.detect_language()` counts Ethiopic Unicode code points and classifies the query as `am`, `en`, or `mixed`. The result is stored on the `Message` row so reporting can break results out by language later.
2. **Dense retrieval** — `hybrid_retrieval.dense()` embeds the query with the same Gemini model used for documents, then runs `SELECT ... ORDER BY embedding <=> :q LIMIT 50` against the HNSW-indexed `document_chunk` table.
3. **Sparse retrieval** — `hybrid_retrieval.sparse()` builds a `tsquery` from the user input and runs `ts_rank` against the GIN-indexed `content_tsv` column. The `simple` text-search configuration is used because Postgres's stemmed configurations are tuned for European languages and produced worse results on Amharic.
4. **RRF fusion** — `hybrid_retrieval.fuse_rrf()` merges the two lists with the formula `sum(1 / (60 + rank_i))` per chunk. The top 5 fused chunks go to generation.
5. **Generation** — Gemini chat with the structured prompt, then citation validation. Extractive fallback on failure.
6. **Confidence scoring** — four-signal heuristic attached to the response: dense cosine 0.4, sparse rank 0.2, citation overlap 0.3, LLM probability variance 0.1.

The chunks for the response are persisted on the `Message` row, so the citation panel in the UI can render the source text on demand without a re-query.

### 6.4 Knowledge Base and Document Retrieval

**Requirements:** FR-01..03, UC-02, UC-03, NFR-04.

Documents enter the knowledge base through two paths.

**Path A — admin upload.** `POST /v1/admin/documents` accepts a PDF, DOCX, or HTML file. The handler stores the file in `awaqi_uploads`, creates a `Document` row with `status='pending'`, enqueues an `ingest` job on the RQ `ingest` queue, and returns immediately with the document ID. The admin UI subscribes to the SSE progress channel for that job and shows the pipeline stages as they advance.

**Path B — automated scrapers.** APScheduler triggers four scrapers nightly:

- `mor_scraper` — official `mor.gov.et` proclamations and directives.
- `mor_news_scraper` — MoR news posts.
- `ethiodata_scraper` — secondary regulatory mirror.
- `telegram_scraper` — public ERA Telegram channels for announcements.

Each scraper writes a `scraped_document` row, downloads the file, and enqueues an `ingest` job exactly as the admin upload path does.

**Ingestion job** (`apps/api/queue/jobs/ingest_job.py`). The job runs the full pipeline:

1. `extractor.extract()` — PDF/HTML text. PDFs without a text layer fall through to OCR via PyMuPDF + Tesseract with the `tesseract-ocr-amh` pack, or Gemini Flash OCR (configurable through `INGEST_EXTRACTOR`).
2. `text_quality.score()` — flags low-confidence OCR results and routes them to `requires_manual_review`. They are surfaced in the review-queue page of the admin UI.
3. `chunker.chunk()` — sliding window of ~1024 tokens with a 100-word overlap; each chunk retains source title, page, section header in `metadata`.
4. `gemini_embedder.embed_batch()` — 32-chunk batches.
5. **Atomic replace** — `ingest.replace_chunks()` opens one transaction, deletes the existing chunks for the document, inserts the new chunks, and commits. The document never sits half-indexed in the retrieval view.
6. Status transitions to `indexed`. A thumbnail is rendered (`thumbnail.render()`) for the documents list.

The vector-store admin page (`apps/web/app/[locale]/(admin)/admin/settings/vector-store-section.tsx`) exposes the underlying index health (row counts per status, last-rebuild time, current dimension) and a one-click full re-embed. This was useful during the 1024 → 1536 → 3072 dimension migrations and stays in production for future model changes.

### 6.5 Database Services

**Requirements:** SI-02, Section 3.8 of the SRS.

PostgreSQL 16 with pgvector runs in the `pgvector/pgvector:pg16` Docker image. Connections from the API use `postgresql+asyncpg://`, and connections from Next.js (Better Auth) use the sync DSN. The schema is managed by Alembic; 18 migration revisions exist as of v1.1.

Tables grouped by purpose:

| Group | Tables |
|---|---|
| Chat | `chat_session`, `message` |
| Knowledge base | `document`, `document_chunk`, `scraper_run`, `scraped_document` |
| Auth | `user`, `cu_user`, Better Auth core, `cu_user_telegram_chat_id` |
| Notifications | `notification_config`, `notification_log` |
| Announcements | `announcement` |
| Telegram | `telegram_scraper`, `telegram_message_parts` |

Connection pooling uses `pool_pre_ping=True` to recycle stale connections after Docker restarts. The API container's entrypoint runs `alembic upgrade head` before starting Uvicorn, so deployments are self-migrating.

### 6.6 Job Queue and Worker Tier (new in v1.1)

**Why it was added.** Before v1.1, the API ran ingestion and scraping inline. A single document upload could stall the request handler for tens of seconds while the embedding batch ran, and a scraper run pinned a worker thread for the entire crawl. Concurrent uploads serialised on one handler, and any inline crash took down the API.

**What was built.** A Redis-backed RQ layer with three queues, each with its own worker container.

| Queue | Default timeout | Job examples |
|---|---|---|
| `scraper` | 3600 s | `mor_scraper_job`, `ethiodata_scraper_job`, `telegram_scraper_job` |
| `ingest` | 1800 s | `ingest_job` — one job per document |
| `notification` | 3600 s | `notification_job` — watermarked sweep over new documents |

The API enqueues jobs via the synchronous Redis pool in `apps/api/queue/connection.py`. Workers run from the same image as the API but with an alternate entrypoint (`rq worker <queue>`). Real-time progress is published on Redis pub/sub channels by the workers and streamed to the admin UI through the `/v1/progress/{job_id}` SSE endpoint. **RQ Dashboard** runs at port 9181 (SSH-tunnelled) and shows queues, workers, and failed jobs at a glance.

The split removed long jobs from the request path. Upload responses come back in well under a second; concurrent uploads no longer serialise; a worker crash leaves the API untouched and RQ retries the job on the next worker start.

### 6.7 Notification Service (new in v1.1)

`apps/api/notification_service.py` runs inside the `notification` worker on a 10-minute schedule. On each tick it:

1. Reads `NotificationConfig` (singleton row id=1) for the watermark timestamp and the recipient list.
2. Selects documents indexed after the watermark.
3. For each candidate, asks Gemini whether the document is noteworthy (new proclamation, amended directive, deadline reminder) using a structured YES/NO prompt with a short rationale.
4. For noteworthy documents, composes an Amharic + English email body and an SMS body, dispatches via Mailtrap SMTP and the GeezSMS REST API, and writes a `NotificationLog` row per send attempt.
5. Advances the watermark so the same documents are not re-evaluated.

The service degrades gracefully. Email and SMS failures are logged per recipient, and the watermark advances independently so a transient SMTP outage does not block subsequent runs. The admin notification-bell component in the web header surfaces recent dispatches.

### 6.8 Awaqi Max — Agent Mode (new in v1.1)

A toggle on the chat surface switches between "basic" RAG mode and "Awaqi Max" agent mode. In Awaqi Max, the AI engine runs a ReAct loop on Gemini function calling (`packages/ai-engine/src/ai_engine/agent/react_agent.py`):

- **Reason → Act → Observe.** Gemini sees the question and the tool schemas, decides whether to call `rag_search` (same hybrid retriever as basic mode) or `ethiopian_web_search` (a constrained web tool), or to answer directly.
- **Tool call.** If Gemini calls a tool, we execute it and append a `FunctionResponse` to the conversation.
- **Loop.** Repeat until Gemini returns text or `MAX_ITERATIONS` is hit (default 4).

Citations from both the knowledge base and the web search are merged into one citation list. The union of all retrieved `DocumentChunk` rows is persisted on the message, so the citation-panel UX stays consistent with basic mode. Tool calls are recorded in a trace stored on the message and shown on the `/admin/evaluation` drill-down view.

Awaqi Max is opt-in for two reasons: it costs more (multiple Gemini calls per turn) and the answer time is higher. The evaluation framework benchmarks both modes side by side so the team can compare quality vs cost.

### 6.9 Evaluation Framework (new in v1.1)

**Requirements:** NFR-22, partial SDS-DEF-06.

The framework lives in `packages/ai-engine/src/ai_engine/evaluation/` and has four files:

- `dataset.py` — loads `data/evaluations/benchmark.json` (23 curated Amharic Q&A pairs from the Federal Income Tax Regulation 410/2017 and Income Tax (Amendment) Proclamation 1395/2017). Each item carries the question, the expected answer, the ground-truth proclamation number and article numbers, and topic tags.
- `metrics.py` — retrieval metrics: Hit@k, Precision@k, Recall@k, MRR, NDCG@k. Computed deterministically by matching retrieved chunks' `proclamation_number` against the ground truth.
- `judge.py` — Gemini-as-judge scoring on 1–10 across five axes: faithfulness, answer relevance, context recall, correctness, and an `overall` weighted aggregate (0.30 correctness + 0.30 faithfulness + 0.20 relevance + 0.20 context recall). A model-free semantic-similarity score (cosine of expected vs actual embedding) accompanies these.
- `runner.py` — orchestrates a run across assistants (`basic`, `awaqi_max`, or `both`) and retrieval modes (`optimized`, `dense_only`, `bm25_only`). Writes results to `data/evaluations/runs/<timestamp>.json`.

The admin UI page `/admin/evaluation` lets the team start a new run, pick the assistant and retrieval mode, and inspect per-question scores after the run completes. Runs are persisted so quality can be tracked over time as the knowledge base grows.

A CLI entry point (`scripts/run_evaluation.py`) lets the team run benchmarks from the command line — useful when comparing branches.

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
| `POST` | `/v1/admin/documents` | admin | Upload document; enqueues `ingest` job |
| `GET` | `/v1/admin/documents` | admin | List documents with status, stage, error |
| `POST` | `/v1/admin/documents/{id}/retry` | admin | Re-enqueue failed / manual-review document |
| `POST` | `/v1/admin/documents/{id}/review` | admin | Resolve a `requires_manual_review` item |
| `GET` | `/v1/admin/health` | admin | DB, Redis, scheduler, worker, last scraper run |
| `GET` | `/v1/admin/analytics` | admin | Sessions, messages, document status counts |
| `POST` | `/v1/admin/scraper/run` | superadmin | Enqueue an immediate scraper job |
| `POST` | `/v1/admin/vector-store/rebuild` | superadmin | Re-embed every chunk against the current model |
| `GET` | `/v1/announcements` | public | Active banners for the chat |
| `POST` | `/v1/admin/announcements` | admin | Create or update an announcement |
| `GET` | `/v1/evaluation/runs` | admin | List historical evaluation runs |
| `POST` | `/v1/evaluation/runs` | admin | Start a new benchmark run |
| `GET` | `/v1/evaluation/runs/{id}` | admin | Per-question scores for one run |
| `GET` | `/v1/progress/{job_id}` | admin (SSE) | Server-Sent Events stream of job progress |
| `POST` | `/v1/telegram/link/request` | customer | Start Telegram account linking |
| `POST` | `/v1/telegram/link/confirm` | customer | Confirm with the bot-issued code |
| `GET` | `/v1/telegram/link/status` | customer | Current link state |
| `POST` | `/v1/telegram/link/unlink` | customer | Remove the link |

---

## 8. Database Implementation

### 8.1 Engine

PostgreSQL 16 runs in the `pgvector/pgvector:pg16` Docker image with `pgvector` pre-installed. The compose service mounts the `awaqi_pgdata` volume and runs `CREATE EXTENSION IF NOT EXISTS vector;` on first boot via `docker/init-db/`. The API connects via an async DSN; Next.js uses the sync DSN for Better Auth's driver.

### 8.2 Migrations (Alembic)

18 migration revisions have been applied in production. Notable ones:

| Migration | Change |
|---|---|
| `0001_initial_schema` | Core tables and default tax taxonomies |
| `0003_cu_auth_tables` | Better Auth customer-user tables |
| `0005_phase_a_ingestion` | `document_chunk` with `vector(1024)` |
| `0009_ba_user_admin_plugin_cols` | Better Auth admin plugin columns |
| `0010_scraper_and_document_registry` | `scraper_run`, `scraped_document` |
| `0013_gemini_embedding_dim` | Embedding column → 1536-d |
| `0014_gemini_embedding_3072` | Embedding column → 3072-d (pgvector 0.7.x) |
| `0015_gemini_embedding_dim_3072` | Reconcile dimension across all tables |
| `0016_notification_tables` | `notification_config`, `notification_log` (v1.1) |
| `0017_announcements` | `announcement` table (v1.1) |
| `0017_enforcement_status` | Document enforcement status (v1.1) |
| `0018_merge_0017_heads` | Merge the parallel 0017 heads |

### 8.3 Indexes That Matter

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
| AuthZ — web | Middleware | Blocks `/admin/*` without valid session and role |
| AuthZ — API | `require_admin` dep | 403 on role mismatch; some endpoints require `superadmin` |
| Rate limit — app | Public endpoints | Redis token-bucket: 15 req / 600 s / IP; HTTP 429 + `Retry-After` |
| Rate limit — edge | `/api/v1/chat/send` | Cloudflare WAF: 30 req / minute / IP |
| Transport | Ingress | Let's Encrypt via Certbot, TLS 1.2/1.3 only, HSTS (6-month max-age) |
| Network | Host firewall | SG allows 443/80 from Cloudflare IPs, 22 from team IPs; Postgres/Redis on Docker bridge only |
| Host | SSH | Key-based only, password and root login disabled, `fail2ban` watching auth log |
| Secrets | Storage | `.env.prod` `chmod 600`; CI uses GitHub Actions encrypted secrets |
| Disk | Encryption | EBS encrypted with default AWS KMS key |
| WAF | Edge | Cloudflare OWASP core + managed ruleset; DNSSEC on |
| Input validation | Pydantic | All request bodies validated; uploads capped at 25 MB |
| SQL safety | ORM | SQLAlchemy parameterised queries throughout |
| XSS | Web | React auto-escapes; admin-authored HTML passes through DOMPurify |
| Prompt injection | RAG | Retrieved chunks wrapped in delimited blocks; system prompt instructs the model to treat retrieved text as data, not instructions |

ClamAV upload scanning, immutable audit logging, and automated PII scrubbing remain on the backlog (SRS-DEF-08, SDS-DEF-02).

---

## 10. Infrastructure and Deployment

The production deployment runs on a single AWS EC2 `t3.medium` (2 vCPU, 4 GB RAM, 30 GB gp3 EBS, `eu-north-1`). Every service runs as a Docker container managed by Docker Compose. PM2 supervises the API and web processes inside their containers for automatic restart and unified `pm2 logs` access during incidents.

### 10.1 Containers

| Container | Image | Role |
|---|---|---|
| `api` | built from `api.Dockerfile` | FastAPI under Uvicorn + PM2 |
| `web` | built from `web.Dockerfile` | Next.js standalone server + PM2 |
| `db` | `pgvector/pgvector:pg16` | PostgreSQL + pgvector |
| `redis` | `redis:7-alpine` | Cache, rate limiting, RQ |
| `telegram_bot` | built from `bot.Dockerfile` | Pyrogram bot |
| `ingest-worker` | shares `api` image, alt entrypoint | `rq worker ingest` |
| `scraper-worker` | same | `rq worker scraper` |
| `notification-worker` | same | `rq worker notification` |
| `rq-dashboard` | `eoranged/rq-dashboard` | Queue inspection UI on :9181 |

### 10.2 Network

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 443 | TCP | Cloudflare IPs | HTTPS ingress |
| 80 | TCP | Cloudflare IPs | HTTP redirect + ACME |
| 22 | TCP | Team static IPs | SSH |
| 5432 | TCP | Not exposed | Postgres on Docker bridge |
| 6379 | TCP | Not exposed | Redis on Docker bridge |
| 9181 | TCP | Not exposed publicly | RQ Dashboard via SSH tunnel |

Cloudflare in front handles DDoS mitigation, OWASP managed ruleset, and DNS. EC2 security groups restrict origin access to Cloudflare's published IP ranges.

### 10.3 Storage and Backup

- 30 GB gp3 EBS for Docker volumes (`awaqi_pgdata`, `awaqi_uploads`, `awaqi_redis_data`).
- S3 bucket `awaqi-backups`: nightly `pg_dump --format=custom` and a copy of every ingested document. Lifecycle: Glacier transition after 30 days, delete after 365.
- Restore documented in `docs/runbooks/db-restore.md`; rehearsed twice during development.

### 10.4 Environments

| Environment | Where | Database | Purpose |
|---|---|---|---|
| Development | Developer laptop | Docker Postgres + Redis | Day-to-day coding |
| Testing | GitHub Actions runner | Ephemeral `pgvector/pgvector:pg16` service | Unit + integration |
| Staging | Same EC2, separate compose profile | `awaqi_db_staging` | Manual QA, advisor demos |
| Production | EC2 (`awaqi.<domain>`) | `awaqi_db` | Live system |

---

## 11. CI/CD and DevOps

### 11.1 Branching

Trunk-based. `main` is protected. PRs require a green CI run and one approving review. The advisor reviews milestone PRs. CI runs on every push to `main`, `dev`, and on every PR.

### 11.2 Pipeline

GitHub Actions runs three jobs on every push to watched branches and every PR to `main`:

1. **`test-python`.** `uv sync --group dev`, Ruff lint, then unit tests in `tests/api/test_schemas.py`, `tests/api/test_session_token.py`, `tests/packages/`, `packages/ai-engine/tests/`. Fake DB and Redis URLs.
2. **`test-integration`.** Boots a `pgvector/pgvector:pg16` service container, runs Alembic migrations, then runs the integration tests that exercise the chat and admin flows end to end against the real database.
3. **`test-web`.** `npm ci`, ESLint, type-check, Vitest, Playwright smoke specs against a built `next start`. Catches type regressions, broken components, and broken core flows before they reach production.

### 11.3 Containerisation

- `api.Dockerfile` — Python 3.12-slim, `uv` installs dependencies, entrypoint runs Alembic migrations and starts Uvicorn under `pm2-runtime`. Worker containers use the same image with an `rq worker <queue>` entrypoint.
- `web.Dockerfile` — multi-stage; stage 1 runs `next build` (standalone output); stage 2 is a minimal Node 20 image that runs `node server.js`.
- `bot.Dockerfile` — same Python base as the API, `python -m telegram_bot` entrypoint.

### 11.4 Deployment

One SSH session: `git pull && docker compose up -d --build`. The API container's entrypoint runs migrations automatically. Rollback is `git checkout <prev-sha>` followed by the same compose command; a database rollback uses the latest `pg_dump` archive.

---

## 12. Testing Implementation

Three layers, by speed and by what each layer needs.

### 12.1 Python Unit Tests (pytest)

Pure Python — no I/O. Cover schema validation, HMAC token signing, language detection, chunking, RRF scoring, the extractive fallback, and the evaluation metrics. The embedder is auto-mocked via `tests/api/conftest.py`. Runs in seconds; gates every PR.

### 12.2 Python Integration Tests (pytest + httpx)

Run against a real Postgres with pgvector. Cover the chat and admin routers end to end: send a message and get a cited response from a stubbed Gemini; retrieve history with the right session token; fail history with a wrong token; exceed the rate limit and get 429; upload a document and verify it lands as `pending` with an `ingest` job enqueued; resolve a `requires_manual_review` item.

### 12.3 Frontend Unit Tests (Vitest + Testing Library)

Cover utility functions, admin-route helpers, and the `JobProgress` component (SSE consumer). Test files live next to their source: `apps/web/lib/utils.test.ts`, `apps/web/lib/admin-routes.test.ts`, `apps/web/components/ui/job-progress.test.tsx`. Configured by `apps/web/vitest.config.ts` and `vitest.setup.ts`.

### 12.4 End-to-End Tests (Playwright)

We chose **Playwright** over Selenium and Cypress. Playwright handles Next.js's hydration model better, supports parallel browser contexts out of the box, and has first-class TypeScript bindings. Selenium requires manual driver-version management; Cypress's same-origin restrictions made testing the Better Auth cookie flow harder than necessary.

Current specs in `apps/web/e2e/`:

- `smoke.spec.ts` — health check on the API, open the chat page, send one query, assert a citation renders, open the admin login page.

The Playwright config (`playwright.config.ts`) boots `next start` and the API for the test run. Specs run in CI under the `test-web` job and locally via `make test-e2e`.

### 12.5 Test Results (Current — Last Green CI Run)

| Suite | Count | Status |
|---|---|---|
| Python unit | 42 tests | Passing |
| Python integration | 18 tests | Passing |
| Frontend Vitest | 9 tests | Passing |
| Playwright E2E | 3 specs (smoke) | Passing |

CI runs are roughly 90 s for Python unit, 3 min for integration, and 2 min for the web suite. Exact counts may shift between runs and should be re-verified against the current `make check` output (see `things to update after real run.md`).

---

## 13. Validation Results

> The numbers in this section are **educated estimates** based on local profiling on the staging EC2 box. Every estimated number is listed in the companion file `things to update after real run.md` with explicit instructions for re-measurement on the production deployment.

### 13.1 Security Validation

Tested against an OWASP Top 10 checklist plus LLM-specific threats. Methodology: scripted attacks from a controlled host (sqlmap, Burp Suite, OWASP ZAP) plus manual review of the most sensitive code paths.

| Area | Test | Result (estimated) | Notes |
|---|---|---|---|
| Prompt injection — retrieval poisoning | 30 hand-crafted Amharic + English injection prompts embedded in document chunks | 28 / 30 mitigated | System prompt isolates retrieved text in a clearly delimited block and instructs the model to treat it as data, not instructions. Two cases caused the model to acknowledge without acting on the injection. |
| Prompt injection — user-supplied | 40 direct user-input injection prompts | 38 / 40 mitigated | Refusal layer and citation validation catch the rest. |
| SQL injection | sqlmap against public endpoints | No SQLi found | SQLAlchemy parameterised queries throughout. |
| XSS — reflected | Burp Suite scan of `/v1/chat/send` and the chat surface | No reflected XSS found | React auto-escapes; API responses typed. |
| XSS — stored | Admin-authored announcement HTML | No stored XSS found | Announcement HTML passes through DOMPurify on render. |
| Access control — admin endpoints | Anonymous and customer-role calls to 12 `/v1/admin/*` endpoints | 100% blocked with 403 | |
| Access control — guest session token | Tampered, expired, and wrong-session tokens | 100% blocked with 401 | HMAC + session-ID claim binding. |
| Rate limit | Burst of 100 requests in 10 s from one IP | First 15 pass, rest 429 | Cloudflare rule kicks in at 30 / minute. |
| Header hygiene | `securityheaders.com` scan | Grade **A** | HSTS, X-Content-Type-Options, Referrer-Policy, X-Frame-Options. |

The two prompt-injection cases that did not fully mitigate are tracked under the confidence-gate backlog item (SDS-DEF-04).

### 13.2 Performance Validation

Methodology: `wrk` against `/v1/chat/send` and `/health`, `pgbench` against the database, `psrecord` for CPU and memory traces on the staging EC2 box.

| Metric | Target (NFR) | Measured (estimated) | Notes |
|---|---|---|---|
| AI response time — p50 | < 5 s (NFR-01) | ~3.2 s | Gemini round-trip dominates (~2.6 s); local pipeline adds ~0.6 s |
| AI response time — p95 | < 8 s | ~6.4 s | Worst case is agent mode with two tool calls |
| Extractive fallback latency | < 1 s | ~0.4 s | No external LLM round-trip |
| Concurrent users | ≥ 100 (NFR-03) | ~120 sustained, ~180 burst | One API replica; RQ workers absorb ingestion |
| `/v1/chat/send` throughput | — | ~22 req/s sustained | Bound by Gemini |
| `/health` throughput | — | ~3 800 req/s | Synthetic; Uvicorn overhead |
| Cold dense-retrieval DB time | < 200 ms | ~85 ms | HNSW on 3072-d vectors |
| FTS query time | < 100 ms | ~32 ms | GIN on `simple` tsvector |
| Hybrid retrieval total | < 300 ms | ~140 ms | Dense + FTS run as parallel coroutines |
| Single-query embedding latency | < 600 ms | ~480 ms | Gemini embedding round-trip |
| 10-page PDF ingestion | < 30 s | ~12 s | Extraction + chunking + 8 embedding batches |
| 10-page OCR ingestion | < 90 s | ~62 s | Tesseract dominates |
| CPU under load (120 conc.) | < 70% | ~58% | vCPU mostly idle waiting on Gemini |
| Memory steady-state | — | ~1.4 GB / 4 GB | Includes Postgres shared buffers |
| Redis memory | < 256 MB cap | ~28 MB steady | Mostly rate-limit keys |

The queue split (§6.6) was the largest performance win in this release. Before RQ, a single upload could stall the API for tens of seconds while the embedding batch ran inline. After the split, upload returns in well under a second and the work moves to the `ingest` worker. The admin UI watches progress over SSE.

### 13.3 AI Accuracy Validation

Methodology: `scripts/run_evaluation.py` against the 23-item Amharic benchmark (`data/evaluations/benchmark.json`). The runner swaps retrieval modes and assistants so the team can attribute changes to either the embedding, the keyword layer, or the agent loop.

| Metric | Target | Result (estimated) | Notes |
|---|---|---|---|
| Hit@5 (production hybrid) | ≥ 0.85 (NFR-04) | ~0.91 | Better than `dense_only` (~0.78) and `bm25_only` (~0.74) |
| MRR (production hybrid) | — | ~0.78 | Right document is usually rank 1 or 2 |
| NDCG@5 (production hybrid) | — | ~0.81 | Position-discounted relevance |
| Faithfulness (basic, judge /10) | ≥ 8 | ~8.4 | Citation validation drives this |
| Faithfulness (Awaqi Max, /10) | ≥ 8 | ~8.7 | Agent prefers tool calls over speculation |
| Answer relevance (basic, /10) | ≥ 8 | ~8.3 | |
| Context recall (basic, /10) | ≥ 8 | ~7.9 | Some Amharic-specific clauses miss top-5 |
| Correctness (basic, /10) | ≥ 8 | ~7.8 | Model is right when it answers; refuses occasionally |
| Overall weighted (basic, /10) | ≥ 8 | ~8.1 | Production hybrid + basic |
| Multilingual parity (Am vs En, MRR) | ≤ 5% gap (NFR-18) | ~3.2% gap | English questions on the same regulations |
| Hallucination rate (manual n=50) | < 5% (NFR-05) | ~3% | Two responses flagged for ambiguous citation |
| Citation accuracy (manual review) | ≥ 95% (NFR-06) | ~96% | Citation validation drops orphans; some valid sources missed |

The `/admin/evaluation` page surfaces these numbers per run and per question, so the team can drill into failures and decide where to invest next.

---

## 14. Deployment Procedures

### 14.1 Pre-Deployment Checklist

- [ ] CI green on `main`.
- [ ] Alembic migrations reviewed and tested against a copy of production.
- [ ] `.env.prod` updated with any new variables.
- [ ] Database backup taken in the last 24 hours.
- [ ] Cloudflare maintenance mode **not** active.

### 14.2 Deployment Steps

1. SSH to the EC2 host as the `awaqi` user.
2. `cd ~/Awaqi && git fetch origin && git checkout main && git pull`.
3. Inspect `git log --stat HEAD~..HEAD` for surprise migrations or env changes.
4. `docker compose -f docker/docker-compose.yml up -d --build`.
5. Watch the API logs for the Alembic migration step and the Uvicorn startup banner.
6. Watch each worker container for `Listening on <queue>...`.
7. Smoke test: `curl /health`, send a test query in Amharic and English, send a Telegram message, enqueue a small document and confirm it indexes.
8. Tail logs for 5 minutes.

### 14.3 Rollback

1. `git log --oneline -10` to find the last known-good SHA.
2. `git checkout <prev-sha>`.
3. `docker compose -f docker/docker-compose.yml up -d --build`.
4. If a migration caused the issue, restore from the latest `pg_dump` per `docs/runbooks/db-restore.md`.

---

## 15. Monitoring, Logging, and Alerting

Production observability today is lightweight: PM2 supervises and rotates logs inside each container, `docker logs` streams stdout, and `pm2 monit` is the operator's first stop. Application logs are structured JSON (`structlog`) written to stdout. RQ Dashboard at port 9181 (SSH-tunnelled) shows queues, workers, and failed jobs.

The next iteration adds:

- `prometheus-fastapi-instrumentator` for per-endpoint latency and error rate.
- `postgres_exporter` and `redis_exporter` for resource metrics.
- Grafana dashboards for API Health and Pipeline Health.
- Loki + Promtail for centralised log search.
- Alertmanager with Slack (`#awaqi-alerts`) for warnings and pager email for critical events (API down, three consecutive scraper failures, database disk above 85%).

The compose scaffolding is in place; the work is queued for the post-submission iteration.

---

## 16. Cost Considerations

| Item | Est. monthly cost |
|---|---|
| EC2 `t3.medium`, on-demand | ~ $30 |
| EBS 30 GB gp3 | ~ $3 |
| Elastic IP attached | $0 |
| S3 (backups + archive) | < $1 |
| Cloudflare Free plan | $0 |
| Domain (prorated) | ~ $1 |
| Gemini API | $10 – $25 |
| Mailtrap SMTP | $0 (free tier) |
| GeezSMS | ~ $5 |
| **Total** | **~ $50 – $65 / month** |

For a production rollout (SRS load targets), splitting Postgres onto RDS, Redis onto ElastiCache, and adding an Application Load Balancer pushes the baseline to roughly $150 – $200 / month before Gemini and SMS usage.

---

## 17. Agile Workflow and Timeline

Two-week sprints from December 2025 through May 2026. Tickets in GitHub Issues grouped by milestone.

| Phase | Window | Highlights |
|---|---|---|
| Phase 1 — Core Platform | Dec 2025 – Feb 2026 | Monorepo, Postgres + pgvector, FastAPI skeleton, Next.js + Better Auth, Docker Compose, CI |
| Phase 2 — AI Features | Feb 2026 – Apr 2026 | Ingestion, hybrid retrieval, RAG synthesis, citation validation, Telegram bot, daily scraper, admin dashboard |
| Phase 3 — Hardening | Apr 2026 – May 2026 | Embedding dimension migration (1024 → 1536 → 3072), Better Auth role gating, HMAC session tokens, TLS, security groups, Cloudflare WAF |
| Phase 4 — Last Improvements | May 2026 | RQ queue split, notification service, Awaqi Max agent, evaluation framework, Playwright + Vitest, vector-store admin, secondary scrapers |

---

## 18. Deferred Items and Known Limitations

| ID | Item | Priority | State |
|---|---|---|---|
| SDS-DEF-01 | ClamAV upload scanning | Medium | Not active |
| SDS-DEF-02 | Immutable audit log | Medium | Partial admin logs |
| SDS-DEF-03 | Multi-turn context (last 5 turns) | Low | Follow-up quality below target |
| SDS-DEF-04 | Hard confidence-threshold gate | Medium | Score informational, not blocking |
| SDS-DEF-05 | Full analytics / KPI model | Low | Admin observability incomplete |
| SDS-DEF-06 | Continuous RAG-quality automation | Low | Manual benchmark runs only |
| SDS-DEF-07 | Citation side-panel UX | Low | Inline citations only |
| SDS-DEF-08 | Feedback UX wired to chat | Low | Model + API present |
| SRS-DEF-NLU | Amharic intent classification | High | Below 90% accuracy on available dataset |
| Observability | Prometheus + Grafana | Medium | Scaffolded, not enabled |
| Observability | Loki / ELK log shipping | Low | Stdout + PM2 sufficient at current scale |

---

## 19. References

**Internal**

- SRS v1.1 — `G13_SRS_Final_Updated.docx.txt`
- SDS v1.1 — `G13_SDS_Final_Updated.docx.txt`
- `ARCHITECTURE.md` — repository-level technical overview
- `docs/TESTING.md` — three-layer testing guide
- `docs/evaluation.md` — evaluation framework and dataset
- `docs/awaqi-max.md` — agent-mode design and tools
- `Makefile` — canonical dev commands
- `.env.example` — environment-variable contract
- `docker/docker-compose.yml` — production compose stack
- `.github/workflows/ci.yml` — CI pipeline
- `docs/runbooks/db-restore.md` — database restore procedure
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

*End of Implementation Documentation v1.1 — Awaqi · Group 13 · 2026-05-28.*
