# AI Engine Package
## `ai-engine`

Core AI logic for Awaqi. Right now this package is focused on **document ingestion** (PDF → chunks → embeddings → database). The **RAG answering pipeline** is planned but not yet wired into the chat endpoint.

## What this package does today

- **Extract text from PDFs** using **Gemini Flash** (handles scanned/OCR PDFs as well as digital PDFs).
- **Chunk extracted text** into overlapping chunks with page/offset metadata.
- **Generate embeddings** with **Gemini Embedding** (`gemini-embedding-001`, 1024 dims).
- **Store chunks** in Postgres (`document_chunks.embedding` is a pgvector(1024)).

The main entry point is `ai_engine.ingest.ingest_pdf`, re-exported as `ai_engine.ingest_pdf`.

## Where it’s used

- **Admin upload endpoint**: `apps/api/routers/admin.py` calls `ai_engine.ingest_pdf(...)` after creating a `documents` row.
- **Chat endpoint**: `apps/api/routers/chat.py` currently returns a placeholder response; it includes a TODO stub where the future RAG pipeline will be called.

## Requirements

- **Python**: 3.11+ (this package declares `>=3.11`)
- **Database**: Postgres 16+ with `pgvector` (see `packages/database`)
- **Env**: Google GenAI credentials available to the `google-genai` client (for example via `GOOGLE_API_KEY`)

Dependencies are declared in `packages/ai-engine/pyproject.toml` (managed via `uv` in this monorepo).

## Local development

From the repo root:

```bash
# Install workspace deps (once)
uv sync

# Run the FastAPI server that exercises ai-engine via /v1/admin/upload
uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

To apply DB migrations:

```bash
cd packages/database && uv run alembic upgrade head
```

## API overview

### `ingest_pdf(pdf_bytes, document_id, db, client=None) -> int`

End-to-end ingestion pipeline:

1. `extract_text(...)` (Gemini Flash per page)
2. `chunk_pages(...)`
3. `embed_texts(...)` (Gemini Embedding API)
4. Insert `DocumentChunk` rows (flushes via the provided SQLAlchemy `AsyncSession`)

The caller is responsible for:

- Creating the parent `documents` row
- Managing the transaction lifecycle / commit
- Supplying GenAI credentials (or passing a configured `genai.Client`)

## Key modules

- `src/ai_engine/extractor.py`: PDF → per-page text using Gemini Flash
- `src/ai_engine/chunker.py`: page text → overlapping chunks + metadata (`pages`, `char_start`, `char_end`)
- `src/ai_engine/embedder.py`: chunk text → 1024-dim normalized embeddings
- `src/ai_engine/ingest.py`: orchestrates the ingestion pipeline and stores `DocumentChunk`s

## Notes / gotchas

- **Embedding dimension must stay 1024** to match the existing `document_chunks.embedding` schema.
- The extractor currently sends **one page at a time** (batched in groups of 10 pages for reliability), which is simpler but can be slower on large PDFs.

## Roadmap (next)

- Add a **RAG answering pipeline** for `apps/api/routers/chat.py`:
  - embed query (`task_type=\"RETRIEVAL_QUERY\"`)
  - vector similarity search over `document_chunks`
  - generate answer with citations + confidence score

Core logic for RAG, Hybrid Search, and Confidence Scoring.
