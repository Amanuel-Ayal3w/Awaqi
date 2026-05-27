"""
Unified embedding entry point for RAG (ingest + retrieval).

Both paths use Gemini via ``gemini_embedder`` — do not mix with E5 vectors in pgvector.
"""

from ai_engine.gemini_embedder import (
    EMBEDDING_DIM,
    embed_passages_sync,
    embed_query_sync,
)

__all__ = ["EMBEDDING_DIM", "embed_passages_sync", "embed_query_sync"]
