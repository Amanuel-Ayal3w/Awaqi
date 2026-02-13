# Awaqi API

This is the backend for the Awaqi application, built with FastAPI.

## Prerequisites

- Python 3.12+
- `uv` (Universal Python Project Manager)

## Setup & Run

We use `uv` for dependency management. No need to manually create a venv.

```bash
# Install dependencies and sync environment
uv sync

# Run the server (auto-reloads on change)
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## Endpoints

- `GET /health`: Check service status.
- `GET /v1/chat`: Chat endpoint.
