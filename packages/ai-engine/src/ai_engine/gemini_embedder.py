"""
Gemini embedding for both retrieval queries and document ingestion.

Uses ``gemini-embedding-2`` at output_dimensionality=1536 (pgvector indexes
cap at 2000 dims; 1536 is half the native 3072-d output and still excellent).
The pgvector column is Vector(1536) — see migration 0013.

Task types:
  RETRIEVAL_QUERY    — query time  (hybrid_retrieval.py)
  RETRIEVAL_DOCUMENT — index time  (ingest.py)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-2")
GEMINI_EMBED_DIM = int(os.getenv("GEMINI_EMBED_DIM", "1536"))
# Gemini embedding API allows up to 100 texts per batch request
_BATCH_SIZE = 100


def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    all_vecs: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start : start + _BATCH_SIZE]
        response = client.models.embed_content(
            model=GEMINI_EMBED_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=GEMINI_EMBED_DIM,
            ),
        )
        all_vecs.extend(list(e.values) for e in response.embeddings)
    return all_vecs


def embed_query_gemini_sync(text: str) -> list[float]:
    """Return a 1536-d query embedding (RETRIEVAL_QUERY task type)."""
    return _embed_batch([text], "RETRIEVAL_QUERY")[0]


def embed_passages_gemini_sync(texts: list[str]) -> list[list[float]]:
    """Return 1536-d embeddings for document chunks (RETRIEVAL_DOCUMENT task type)."""
    if not texts:
        return []
    return _embed_batch(texts, "RETRIEVAL_DOCUMENT")
