# Awaqi Web Frontend

Next.js 15 (App Router) frontend for **Awaqi** — an AI-powered tax support assistant for the Ethiopian Ministry of Revenue.

- **Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Better Auth, next-intl
- **Locales:** English (`en`) and Amharic (`am`)
- **Dev port:** `3100`

---

## Routes

All user-facing pages are under `/[locale]/` (`en` or `am`).

### Public

| Route | Description |
|---|---|
| `/[locale]` | Landing page |
| `/[locale]/login` | Customer sign-in |
| `/[locale]/signup` | Customer sign-up |
| `/[locale]/link-telegram` | Confirm Telegram account linking (one-time token from bot) |

### Chat (customer)

| Route | Description |
|---|---|
| `/[locale]/chat` | Main chat UI (RAG-backed tax Q&A) |
| `/[locale]/chat/history` | Past conversations |
| `/[locale]/chat/settings` | Profile and preferences |
| `/[locale]/chat/login` | Chat-scoped login |
| `/[locale]/chat/signup` | Chat-scoped sign-up |

Guest users can chat without signing in. Sessions use an HMAC `X-Session-Token` stored in the browser.

### Admin

| Route | Description |
|---|---|
| `/[locale]/admin/login` | Admin sign-in (Better Auth) |
| `/[locale]/admin` | Dashboard overview |
| `/[locale]/admin/knowledge-base` | Knowledge base management |
| `/[locale]/admin/documents` | Uploaded documents |
| `/[locale]/admin/documents/[id]/review` | Manual document review workspace |
| `/[locale]/admin/scraper` | MoR web scraper — trigger runs and view live output |
| `/[locale]/admin/telegram` | Telegram channel scraper config |
| `/[locale]/admin/analytics` | Usage analytics |
| `/[locale]/admin/users` | User management (**superadmin** only) |
| `/[locale]/admin/settings` | System settings |
| `/[locale]/admin/settings/logs` | Application logs |

**RBAC:** `admin` and `editor` roles can access the admin panel. `superadmin` is required for user management.

---

## Project structure

```
apps/web/
├── app/
│   ├── [locale]/              # Locale-prefixed routes
│   │   ├── (admin)/           # Admin layout + pages
│   │   ├── (chat-app)/        # Chat layout + pages
│   │   ├── (chat-auth)/       # Chat login/signup
│   │   └── link-telegram/     # Telegram link confirmation
│   └── api/
│       ├── auth/              # Better Auth (admin)
│       └── customer-auth/     # Better Auth (customer)
├── components/
│   ├── admin/                 # Admin sidebar, document review, charts
│   ├── auth/                  # Login/signup forms
│   ├── chat/                  # ChatInterface, MessageList, ChatInput
│   ├── landing/               # Marketing page sections
│   ├── layout/                # Shared header, sidebar, theme toggle
│   └── ui/                    # shadcn/ui primitives
├── lib/
│   ├── api.ts                 # Axios client → FastAPI backend
│   ├── auth.ts                # Admin Better Auth server config
│   ├── customer-auth.ts       # Customer Better Auth server config
│   └── chat-session.ts        # Guest session ID + token helpers
├── messages/                  # i18n strings (en.json, am.json)
└── types/api.ts               # Shared API TypeScript types
```

---

## Environment variables

Next.js loads env from the **monorepo root first**, then **apps/web**, via `loadEnvConfig` in `next.config.ts`. Copy the example from repo root:

```bash
# From repository root
cp apps/web/.env.example .env
```

Required:

| Variable | Purpose |
|---|---|
| `DATABASE_URL_SYNC` | PostgreSQL sync URL for Better Auth (`postgresql://…`, not `asyncpg`) |
| `BETTER_AUTH_SECRET` | Auth signing secret — **at least 32 characters** (`openssl rand -base64 32`). Required for `next start`; `next build` succeeds with a missing/short secret but you must set a real value before production. |
| `NEXT_PUBLIC_APP_URL` | Frontend origin, e.g. `http://localhost:3100` |
| `NEXT_PUBLIC_API_URL` | FastAPI backend, e.g. `http://localhost:8000` |

Optional:

| Variable | Purpose |
|---|---|
| `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` | Used by `npm run seed:superadmin` |

The FastAPI backend must be running for chat, admin API calls, and document ingestion to work.

---

## Getting started

### From monorepo root (recommended)

```bash
# Start Postgres + Redis
docker compose -f docker/docker-compose.yml up -d db redis

# Run migrations
cd packages/database && uv run alembic upgrade head && cd ../..

# Export env (example)
export BETTER_AUTH_SECRET="$(openssl rand -base64 32)"
export DATABASE_URL_SYNC="postgresql://postgres:postgres@localhost:5432/awaqi_db"
export NEXT_PUBLIC_APP_URL="http://localhost:3100"
export NEXT_PUBLIC_API_URL="http://localhost:8000"

# Frontend only
make front

# Or backend + frontend + telegram bot together
make dev
```

### From `apps/web`

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3100](http://localhost:3100).

---

## Chat UI

The chat interface (`components/chat/`) talks to `POST /v1/chat/send` on the FastAPI backend.

**Features:**
- Markdown rendering for assistant replies (GFM)
- Citation sources in a compact popover (book icon + count) below each reply
- Per-message actions: copy, thumbs up/down, export transcript
- Guest sessions with `session_id` + `X-Session-Token` header
- Signed-in customers use Better Auth bearer tokens

---

## Authentication

Two separate Better Auth instances:

| Audience | Config | API routes |
|---|---|---|
| **Admin** | `lib/auth.ts` | `/api/auth/[...all]` |
| **Customer** | `lib/customer-auth.ts` | `/api/customer-auth/[...all]` |

The shared Axios client (`lib/api.ts`) attaches the correct session token automatically — admin routes use the admin session, everything else uses the customer session.

Seed a superadmin (requires `DATABASE_URL_SYNC` in root `.env`):

```bash
cd apps/web
npm run seed:superadmin
```

---

## Scripts

```bash
npm run dev           # Dev server on port 3100
npm run build         # Production build (includes TypeScript check)
npm run start         # Start production server
npm run type-check    # tsc --noEmit
npm run seed:superadmin
```

From repo root:

```bash
cd apps/web && npx tsc --noEmit   # Type-check only
make check                          # Full monorepo check (includes web build)
```

---

## Docker

The web service is defined in `docker/docker-compose.yml` and built from `docker/web.Dockerfile`. It maps host port `3000` → container port `3100`.

```bash
docker compose -f docker/docker-compose.yml up --build web
```

---

## Related docs

- [Backend API](../api/) — FastAPI gateway
- [Monorepo README](../../README.md) — full system overview
- [AGENTS.md](../../AGENTS.md) — dev commands and gotchas
