"""
Hybrid retrieval: dense (pgvector) + sparse (BM25) fused with RRF (SDS §4.6.4).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Sequence

from database import bm25_search_chunk_ids, vector_search_chunk_ids
from database.models.document import DocumentChunk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.embeddings import embed_query_sync
from ai_engine.query_nlu import build_retrieval_query_text

logger = logging.getLogger(__name__)

RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[uuid.UUID]],
    *,
    k: int = RRF_K,
    top_n: int = 12,
) -> list[uuid.UUID]:
    """RRF score = Σ 1/(k + rank_i); return top_n chunk ids by fused score."""
    scores: dict[uuid.UUID, float] = {}
    for ids in ranked_lists:
        for rank, cid in enumerate(ids, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return ordered[:top_n]


async def retrieve_fused_chunk_ids(
    db: AsyncSession,
    user_query: str,
    *,
    taxpayer_category: str | None,
    vector_limit: int = 20,
    bm25_limit: int = 20,
    bm25_candidate_pool: int = 200,
    fused_top: int = 10,
) -> list[uuid.UUID]:
    q_for_vec = build_retrieval_query_text(user_query, taxpayer_category=taxpayer_category)

    def _embed() -> list[float]:
        # Unified embedding entry point (Gemini). Keep ingest+retrieval consistent.
        return embed_query_sync(q_for_vec)

    vec_task = asyncio.to_thread(_embed)
    bm25_task = bm25_search_chunk_ids(
        db,
        user_query,
        limit=bm25_limit,
        candidate_pool=max(bm25_limit, bm25_candidate_pool),
    )
    embedding, bm25_ids = await asyncio.gather(vec_task, bm25_task)

    vec_ids = await vector_search_chunk_ids(db, embedding, limit=vector_limit)
    fused = reciprocal_rank_fusion([vec_ids, bm25_ids], top_n=fused_top)
    logger.debug(
        "hybrid_retrieval vec=%d bm25=%d fused=%d",
        len(vec_ids),
        len(bm25_ids),
        len(fused),
    )
    return fused


async def load_chunks_by_ids(
    db: AsyncSession, ids: list[uuid.UUID]
) -> list[DocumentChunk]:
    if not ids:
        return []
    result = await db.execute(select(DocumentChunk).where(DocumentChunk.id.in_(ids)))
    rows = list(result.scalars().all())
    order = {cid: i for i, cid in enumerate(ids)}
    rows.sort(key=lambda c: order.get(c.id, 999))
    return rows
