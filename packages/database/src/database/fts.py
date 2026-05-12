"""PostgreSQL full-text search helpers for document_chunks (AWA-15)."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def fts_search_chunk_ids(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 20,
) -> list[uuid.UUID]:
    """
    Return chunk ids ranked by ts_rank_cd for a simple plain-text query.

    Uses the ``simple`` text search config on generated ``content_tsv``.
    """
    if not query.strip():
        return []

    stmt = text(
        """
        SELECT id
        FROM document_chunks
        WHERE content_tsv @@ plainto_tsquery('simple', :q)
        ORDER BY ts_rank_cd(content_tsv, plainto_tsquery('simple', :q)) DESC
        LIMIT :lim
        """
    )
    result = await db.execute(stmt, {"q": query.strip(), "lim": limit})
    return [row[0] for row in result.fetchall()]
