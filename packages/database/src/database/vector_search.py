"""Dense vector similarity search over ``document_chunks`` (pgvector cosine)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _vector_literal(vec: Sequence[float]) -> str:
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


async def vector_search_chunk_ids(
    db: AsyncSession,
    embedding: list[float],
    *,
    limit: int = 20,
) -> list[uuid.UUID]:
    """
    Return chunk ids closest to ``embedding`` using cosine distance ``<=>``.

    Requires ``embedding`` column populated (IVFFlat index optional).
    """
    if not embedding:
        return []
    lit = _vector_literal(embedding)
    stmt = text(
        """
        SELECT id
        FROM document_chunks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :lim
        """
    )
    result = await db.execute(stmt, {"emb": lit, "lim": limit})
    return [row[0] for row in result.fetchall()]
