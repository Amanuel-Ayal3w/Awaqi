"""
Embedding generator using Gemini Embedding API.

Uses gemini-embedding-001 with RETRIEVAL_DOCUMENT task type and
output_dimensionality=1024 to match the existing pgvector schema.
"""

from __future__ import annotations

import logging
import math

import numpy as np
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL = "gemini-embedding-001"
OUTPUT_DIM = 1024
# Gemini Embedding API allows up to 100 texts per batch
_MAX_BATCH_SIZE = 100


async def embed_texts(
    texts: list[str],
    client: genai.Client | None = None,
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """
    Generate normalized embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.
        client: Optional pre-configured genai.Client.
        task_type: Embedding task type (RETRIEVAL_DOCUMENT for indexing,
                   RETRIEVAL_QUERY for search queries).

    Returns:
        List of 1024-dimensional normalized embedding vectors.
    """
    if not texts:
        return []

    if client is None:
        client = genai.Client()

    all_embeddings: list[list[float]] = []
    total_batches = math.ceil(len(texts) / _MAX_BATCH_SIZE)

    for batch_idx in range(total_batches):
        start = batch_idx * _MAX_BATCH_SIZE
        end = min(start + _MAX_BATCH_SIZE, len(texts))
        batch = texts[start:end]

        logger.debug(
            "Embedding batch %d/%d (%d texts)", batch_idx + 1, total_batches, len(batch)
        )

        result = await client.aio.models.embed_content(
            model=MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=OUTPUT_DIM,
            ),
        )

        for emb in result.embeddings:
            normalized = _normalize(emb.values)
            all_embeddings.append(normalized)

    logger.info("Generated %d embeddings (%d-dim)", len(all_embeddings), OUTPUT_DIM)
    return all_embeddings


def _normalize(vec: list[float]) -> list[float]:
    """L2-normalize an embedding vector (per Google's recommendation for sub-3072 dims)."""
    arr = np.array(vec, dtype=np.float64)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()
