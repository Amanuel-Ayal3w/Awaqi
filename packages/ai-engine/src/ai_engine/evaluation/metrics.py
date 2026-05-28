"""Standard retrieval and similarity metrics for RAG evaluation."""

from __future__ import annotations

import math
from collections.abc import Sequence


def hit_at_k(relevant: Sequence[bool], k: int) -> float:
    """1.0 if any of the top-k items is relevant, else 0.0."""
    top = relevant[:k]
    return 1.0 if any(top) else 0.0


def precision_at_k(relevant: Sequence[bool], k: int) -> float:
    top = relevant[:k]
    if not top:
        return 0.0
    return sum(1 for r in top if r) / float(len(top))


def recall_at_k(relevant: Sequence[bool], k: int, *, total_relevant: int) -> float:
    """
    Recall@k. Uses ``total_relevant`` (the true number of relevant documents
    in the corpus) as the denominator. When that is unknown we approximate
    with the number of relevant items found anywhere in ``relevant``.
    """
    if total_relevant <= 0:
        denom = sum(1 for r in relevant if r) or 1
    else:
        denom = total_relevant
    hits = sum(1 for r in relevant[:k] if r)
    return hits / float(denom)


def mrr(relevant: Sequence[bool]) -> float:
    """Mean reciprocal rank for a single query (== reciprocal rank)."""
    for i, r in enumerate(relevant, start=1):
        if r:
            return 1.0 / i
    return 0.0


def dcg_at_k(gains: Sequence[float], k: int) -> float:
    return sum(
        (g / math.log2(i + 1)) for i, g in enumerate(gains[:k], start=1)
    )


def ndcg_at_k(relevant: Sequence[bool], k: int) -> float:
    """Binary-gain NDCG@k."""
    gains = [1.0 if r else 0.0 for r in relevant]
    actual = dcg_at_k(gains, k)
    ideal_gains = sorted(gains, reverse=True)
    ideal = dcg_at_k(ideal_gains, k)
    if ideal <= 0:
        return 0.0
    return actual / ideal


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)
