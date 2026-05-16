"""Sparse retrieval helpers for document_chunks (FTS candidates + BM25 ranking)."""

from __future__ import annotations

import math
import re
import uuid
from collections import Counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _tokenize(text_value: str) -> list[str]:
    """Language-agnostic tokenization for BM25."""
    return TOKEN_RE.findall(text_value.casefold())


def _bm25_scores(
    query_tokens: list[str],
    document_tokens: list[list[str]],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    if not query_tokens or not document_tokens:
        return [0.0] * len(document_tokens)

    n_docs = len(document_tokens)
    avgdl = sum(len(doc) for doc in document_tokens) / n_docs
    doc_freq: Counter[str] = Counter()
    term_freqs: list[Counter[str]] = []

    for doc in document_tokens:
        tf = Counter(doc)
        term_freqs.append(tf)
        doc_freq.update(tf.keys())

    q_terms = set(query_tokens)
    scores: list[float] = []
    for i, tf in enumerate(term_freqs):
        dl = len(document_tokens[i]) or 1
        score = 0.0
        for term in q_terms:
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            df = doc_freq.get(term, 0)
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1.0 - b + b * (dl / max(avgdl, 1e-9)))
            score += idf * (freq * (k1 + 1.0)) / denom
        scores.append(score)
    return scores


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


async def bm25_search_chunk_ids(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 20,
    candidate_pool: int = 200,
) -> list[uuid.UUID]:
    """
    Rank sparse candidates with BM25 and return top chunk ids.

    Candidate generation uses Postgres FTS first, then trigram similarity fallback.
    """
    q = query.strip()
    if not q:
        return []

    fts_stmt = text(
        """
        SELECT id, content
        FROM document_chunks
        WHERE content_tsv @@ plainto_tsquery('simple', :q)
        ORDER BY ts_rank_cd(content_tsv, plainto_tsquery('simple', :q)) DESC
        LIMIT :pool
        """
    )
    result = await db.execute(fts_stmt, {"q": q, "pool": max(limit, candidate_pool)})
    rows = result.fetchall()

    if not rows:
        trgm_stmt = text(
            """
            SELECT id, content
            FROM document_chunks
            WHERE content % :q
            ORDER BY similarity(content, :q) DESC
            LIMIT :pool
            """
        )
        trgm_result = await db.execute(trgm_stmt, {"q": q, "pool": max(limit, candidate_pool)})
        rows = trgm_result.fetchall()
        if not rows:
            return []

    ids = [row[0] for row in rows]
    docs = [_tokenize(str(row[1] or "")) for row in rows]
    query_tokens = _tokenize(q)
    scores = _bm25_scores(query_tokens, docs)

    ranked_idx = sorted(range(len(rows)), key=lambda i: scores[i], reverse=True)
    if not ranked_idx or scores[ranked_idx[0]] <= 0.0:
        return ids[:limit]

    return [ids[i] for i in ranked_idx[:limit]]
