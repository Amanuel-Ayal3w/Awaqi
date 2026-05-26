"""
Gemini embedding for retrieval queries (AWA-14 alt path).

Uses ``gemini-embedding-2`` with task_type=RETRIEVAL_QUERY and
output_dimensionality=1536. pgvector indexes cap at 2000 dimensions, so we
use 1536 (half the native 3072-d output — still excellent quality).
The pgvector column must be Vector(1536) — see migration 0010.

Only used at *query time* by hybrid_retrieval.py.
Document ingestion must also use output_dimensionality=1536 so that query
and document vectors share the same embedding space.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-2")
GEMINI_EMBED_DIM = int(os.getenv("GEMINI_EMBED_DIM", "1536"))


def embed_query_gemini_sync(text: str) -> list[float]:
    """Return a 1536-d query embedding using Gemini embedding-2."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    response = client.models.embed_content(
        model=GEMINI_EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=GEMINI_EMBED_DIM,
        ),
    )
    return list(response.embeddings[0].values)
