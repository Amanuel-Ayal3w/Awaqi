"""
Ingestion / retrieval ports (SDS Phase A1 — contracts for future wiring).

Concrete storage lives in ``packages/database`` and SQLAlchemy models; hybrid search
is implemented incrementally (vector + FTS). These ``Protocol`` types document the
intended seams without forcing a large refactor today.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class IVectorStore(Protocol):
    """Dense vectors (pgvector) for document chunks."""

    async def replace_document_vectors(
        self,
        document_id: UUID,
        *,
        chunk_rows: list[dict[str, Any]],
    ) -> None:
        """Atomically replace all vectors/chunks for one document."""
        ...


@runtime_checkable
class ISparseSearch(Protocol):
    """Full-text / BM25-style retrieval (PostgreSQL FTS, GIN)."""

    async def search_keywords(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        """Return ranked chunk hits for a keyword query."""
        ...
