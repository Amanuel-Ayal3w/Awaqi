"""
Gemini embeddings for RAG indexing and retrieval (AWA-14).

Uses ``gemini-embedding-001`` with Google-recommended task types:
  - ``RETRIEVAL_DOCUMENT`` for passage/chunk indexing (ingest)
  - ``RETRIEVAL_QUERY`` for user queries (hybrid retrieval)

Both paths MUST use the same model and ``output_dimensionality`` so cosine
search in pgvector is meaningful.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Sequence

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
# Default: 1536-d (half of gemini-embedding-001's native 3072-d output).
# Still excellent RAG quality, and within pgvector's 2000-d index limit for all
# pgvector versions.  Override with GEMINI_EMBEDDING_DIMENSION=3072 only if you
# are running pgvector >= 0.7.0 and have re-run migrations.
GEMINI_EMBEDDING_DIMENSION = int(os.getenv("GEMINI_EMBEDDING_DIMENSION", "1536"))
GEMINI_EMBED_BATCH = int(os.getenv("GEMINI_EMBED_BATCH", "32"))

# Exported for DB schema alignment (see packages/database EMBEDDING_DIM).
EMBEDDING_DIM = GEMINI_EMBEDDING_DIMENSION


def _client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is required for Gemini embeddings. "
            "Set it in .env (https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=api_key)


def _normalize(vec: Sequence[float]) -> list[float]:
    """L2-normalize (required for gemini-embedding-001 when output_dimensionality < 3072)."""
    norm = math.sqrt(sum(float(x) * float(x) for x in vec))
    if norm <= 0:
        return [float(x) for x in vec]
    return [float(x) / norm for x in vec]


def _document_config() -> types.EmbedContentConfig:
    return types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=GEMINI_EMBEDDING_DIMENSION,
    )


def _query_config() -> types.EmbedContentConfig:
    return types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=GEMINI_EMBEDDING_DIMENSION,
    )


def _embed_batch(texts: list[str], *, config: types.EmbedContentConfig) -> list[list[float]]:
    if not texts:
        return []
    client = _client()
    model = GEMINI_EMBEDDING_MODEL
    all_vecs: list[list[float]] = []

    for start in range(0, len(texts), GEMINI_EMBED_BATCH):
        batch = texts[start : start + GEMINI_EMBED_BATCH]
        response = client.models.embed_content(
            model=model,
            contents=batch,
            config=config,
        )
        embeddings = response.embeddings
        if embeddings is None or len(embeddings) != len(batch):
            raise RuntimeError(
                f"Gemini embed_content returned {len(embeddings or [])} vectors "
                f"for {len(batch)} inputs (model={model})"
            )
        for emb in embeddings:
            values = emb.values
            if values is None:
                raise RuntimeError("Gemini embedding missing values")
            vec = _normalize(values)
            if len(vec) != GEMINI_EMBEDDING_DIMENSION:
                raise RuntimeError(
                    f"Expected embedding dim {GEMINI_EMBEDDING_DIMENSION}, got {len(vec)}"
                )
            all_vecs.append(vec)

    return all_vecs


def embed_passages_sync(texts: list[str]) -> list[list[float]]:
    """Embed document chunks for indexing (RETRIEVAL_DOCUMENT)."""
    logger.debug(
        "gemini_embed_passages count=%d model=%s dim=%d",
        len(texts),
        GEMINI_EMBEDDING_MODEL,
        GEMINI_EMBEDDING_DIMENSION,
    )
    return _embed_batch(texts, config=_document_config())


def embed_query_sync(text: str) -> list[float]:
    """Embed a single user query (RETRIEVAL_QUERY)."""
    if not text.strip():
        return []
    vecs = _embed_batch([text.strip()], config=_query_config())
    return vecs[0] if vecs else []
