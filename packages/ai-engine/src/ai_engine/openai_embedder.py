"""
OpenAI embedding for both retrieval queries and document ingestion.

Uses ``text-embedding-3-small`` at 1536 dimensions — matches the pgvector
Vector(1536) column (migration 0013) and the Gemini embedding dimension.

Task types are ignored (OpenAI uses a single embedding space for both query
and document), so the same model is used for both RETRIEVAL_QUERY and
RETRIEVAL_DOCUMENT.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_EMBED_DIM = int(os.getenv("OPENAI_EMBED_DIM", "1536"))
# OpenAI allows up to 2048 inputs per batch request
_BATCH_SIZE = 100


def _embed_batch(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    all_vecs: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start : start + _BATCH_SIZE]
        response = client.embeddings.create(
            model=OPENAI_EMBED_MODEL,
            input=batch,
            dimensions=OPENAI_EMBED_DIM,
        )
        all_vecs.extend(item.embedding for item in response.data)
    return all_vecs


def embed_query_openai_sync(text: str) -> list[float]:
    """Return a 1536-d query embedding."""
    return _embed_batch([text])[0]


def embed_passages_openai_sync(texts: list[str]) -> list[list[float]]:
    """Return 1536-d embeddings for document chunks."""
    if not texts:
        return []
    return _embed_batch(texts)
