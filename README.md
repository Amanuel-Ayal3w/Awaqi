# Awaqi 
This project is a monorepo that contains the following applications:

## Directory Structure

- **`apps/web`**: The Frontend application built with Next.js.
- **`apps/api`**: The Backend API service built with Python and FastAPI.
- **`apps/ai-engine`**: The AI Logic service (RAG, LLM interactions) built with Python.

## How to Run

Each application runs independently. You can open separate terminals to run them.

### 1. Frontend (Next.js)

To run the web application:

```bash
cd apps/web
npm install  # Install dependencies (only first time)
npm run dev
```

The app will be available at `http://localhost:3000`.

### 2. Backend API (FastAPI)

To run the backend service:

**Prerequisite**: Install `uv` (Universal Python Project Manager).

```bash
cd apps/api
uv sync      # Install Python dependencies
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
- Health Check: `http://localhost:8000/health`
- Swagger Docs: `http://localhost:8000/docs`

### 3. AI Engine

(Instructions TBD as this service is developed, currently a placeholder).