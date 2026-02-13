# Awaqi Monorepo

This repository hosts the **Ethio-Revenue-Bot**, an AI-powered tax support assistant for the Ethiopian Ministry of Revenue. It is structured as a monorepo containing independent services (Apps) and shared internal libraries (Packages).

## Directory Structure

```
/ethio-revenue-bot (Monorepo Root)
├── apps/                        # Independent Service Entry Points
│   ├── api/                     # Web Backend Gateway (FastAPI)
│   ├── web/                     # Next.js Frontend (shadcn/ui Monochrome)
│   ├── telegram-bot/            # Telegram Service (@ERATaxBot)
│   └── scraper/                 # Automated Knowledge Ingestor (mor.gov.et)
│
├── packages/                    # Shared Internal Libraries (The "Brains")
│   ├── ai-engine/               # Core RAG, Hybrid Search & Confidence Logic
│   ├── database/                # Shared PostgreSQL + pgvector Schemas
│   ├── nlu/                     # Shared Intent & Language Detection Logic
│   └── utils/                   # Amharic Unicode & Logging Utilities
│
├── docker/                      # Deployment & Orchestration
│   ├── api.Dockerfile           # For the Web Backend
│   ├── web.Dockerfile           # For the Next.js Frontend
│   ├── bot.Dockerfile           # For the Telegram Service
│   ├── scraper.Dockerfile       # For the Ingestion Background Worker
│   └── docker-compose.yml       # Orchestrates all services + DB + Redis
│
├── .github/                     # Change Management & CI/CD
│   └── workflows/               # Automated testing & deployment pipelines
│
├── README.md                    # Project overview & setup instructions

```

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Running with Docker (Recommended)

To spin up the entire system (Database, API, Frontend, Bot, Scraper):

```bash
docker-compose -f docker/docker-compose.yml up --build
```

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/docs
- **Database**: localhost:5432

### Local Development

#### Apps
Each app in `apps/` is a standalone service. Refer to their individual READMEs for specific setup:
- [Web Frontend](apps/web/README.md)
- [Backend API](apps/api/README.md)

#### Packages
Shared logic resides in `packages/`. These are installed into the apps as dependencies.
