"""Admin helpers for pgvector embedding inventory and maintenance."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_VECTOR_TYPE_RE = re.compile(r"vector\((\d+)\)", re.IGNORECASE)


@dataclass(frozen=True)
class VectorStoreStats:
    configured_dimension: int
    embedding_model: str
    column_dimension: int | None
    chunks_total: int
    chunks_with_embedding: int
    chunks_without_embedding: int
    storage_bytes: int
    stored_dimensions: dict[int, int]
    dimension_mismatch: bool

    def to_dict(self) -> dict:
        return {
            "configured_dimension": self.configured_dimension,
            "embedding_model": self.embedding_model,
            "column_dimension": self.column_dimension,
            "chunks_total": self.chunks_total,
            "chunks_with_embedding": self.chunks_with_embedding,
            "chunks_without_embedding": self.chunks_without_embedding,
            "storage_bytes": self.storage_bytes,
            "stored_dimensions": self.stored_dimensions,
            "dimension_mismatch": self.dimension_mismatch,
        }


def configured_embedding_dimension() -> int:
    """Runtime query embedding dimension (must match ingest + ORM column)."""
    return int(os.getenv("GEMINI_EMBEDDING_DIMENSION", "3072"))


def configured_embedding_model() -> str:
    return os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


async def _column_vector_dimension(db: AsyncSession) -> int | None:
    row = (
        await db.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod) AS col_type
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE c.relname = 'document_chunks'
                  AND n.nspname = current_schema()
                  AND a.attname = 'embedding'
                  AND NOT a.attisdropped
                """
            )
        )
    ).one_or_none()
    if row is None:
        return None
    col_type = str(row[0] or "")
    m = _VECTOR_TYPE_RE.search(col_type)
    return int(m.group(1)) if m else None


async def get_vector_store_stats(db: AsyncSession) -> VectorStoreStats:
    configured = configured_embedding_dimension()
    model = configured_embedding_model()
    column_dim = await _column_vector_dimension(db)

    counts = (
        await db.execute(
            text(
                """
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL)::int AS with_emb,
                    COALESCE(SUM(pg_column_size(embedding)), 0)::bigint AS storage_bytes
                FROM document_chunks
                """
            )
        )
    ).one()
    total, with_emb, storage_bytes = int(counts[0]), int(counts[1]), int(counts[2])

    dim_rows = (
        await db.execute(
            text(
                """
                SELECT vector_dims(embedding)::int AS dim, COUNT(*)::int AS cnt
                FROM document_chunks
                WHERE embedding IS NOT NULL
                GROUP BY 1
                ORDER BY 2 DESC
                """
            )
        )
    ).all()
    stored_dims = {int(r[0]): int(r[1]) for r in dim_rows if r[0] is not None}

    mismatch = False
    if column_dim is not None and column_dim != configured:
        mismatch = True
    if stored_dims:
        dominant = max(stored_dims, key=stored_dims.get)
        if dominant != configured:
            mismatch = True
    if column_dim is not None and stored_dims:
        for dim in stored_dims:
            if dim != column_dim:
                mismatch = True
                break

    return VectorStoreStats(
        configured_dimension=configured,
        embedding_model=model,
        column_dimension=column_dim,
        chunks_total=total,
        chunks_with_embedding=with_emb,
        chunks_without_embedding=total - with_emb,
        storage_bytes=storage_bytes,
        stored_dimensions=stored_dims,
        dimension_mismatch=mismatch,
    )


async def wipe_vector_embeddings(db: AsyncSession) -> int:
    """Set all chunk embeddings to NULL (text chunks remain for re-ingest)."""
    result = await db.execute(
        text(
            """
            UPDATE document_chunks
            SET embedding = NULL
            WHERE embedding IS NOT NULL
            """
        )
    )
    return int(result.rowcount or 0)


async def delete_all_document_chunks(db: AsyncSession) -> int:
    """Delete every document chunk row (embeddings and text)."""
    result = await db.execute(text("DELETE FROM document_chunks"))
    return int(result.rowcount or 0)
