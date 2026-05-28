"""
Tools exposed to the Awaqi Max ReAct agent.

Each tool returns a JSON-serialisable dict that becomes the agent's
observation. The agent loop in ``react_agent.py`` wires them into Gemini
function-calling declarations.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field

from database import bm25_search_chunk_ids, vector_search_chunk_ids
from database.models.document import DocumentChunk
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.embeddings import embed_query_sync
from ai_engine.hybrid_retrieval import (
    load_chunks_by_ids,
    reciprocal_rank_fusion,
)
from ai_engine.query_nlu import build_retrieval_query_text

logger = logging.getLogger(__name__)

# Ethiopian sources we bias the web search toward. These should be authoritative
# enough to ground tax / policy answers without hallucinating from random blogs.
ETHIOPIAN_SOURCE_HINT = (
    "mor.gov.et OR site:.et OR mof.gov.et OR mohfw.gov.et OR fanabc.com "
    "OR ena.et OR addisstandard.com OR ethiopianreporter.com OR walta.com"
)


@dataclass
class RagSearchObservation:
    """Returned to the agent after rag_search. Trimmed to keep prompts small."""

    query: str
    chunk_count: int
    chunks: list[dict] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)

    def to_agent_dict(self) -> dict:
        return {
            "query": self.query,
            "chunk_count": self.chunk_count,
            "chunks": self.chunks,
        }


@dataclass
class WebSearchObservation:
    query: str
    summary: str
    citations: list[dict] = field(default_factory=list)
    error: str | None = None

    def to_agent_dict(self) -> dict:
        return {
            "query": self.query,
            "summary": self.summary,
            "citations": self.citations,
            "error": self.error,
        }


async def _retrieve_chunk_ids(
    db: AsyncSession,
    query: str,
    *,
    mode: str,
    k: int,
    taxpayer_category: str | None,
) -> list[uuid.UUID]:
    """Shared retrieval dispatcher: optimized | dense_only | bm25_only."""
    if mode == "bm25_only":
        return await bm25_search_chunk_ids(db, query, limit=k, candidate_pool=200)

    if mode == "dense_only":
        embedding = await asyncio.to_thread(embed_query_sync, query)
        return await vector_search_chunk_ids(db, embedding, limit=k)

    # optimized: hybrid (vector + BM25) + NLU bias
    q_for_vec = build_retrieval_query_text(query, taxpayer_category=taxpayer_category)

    def _embed() -> list[float]:
        return embed_query_sync(q_for_vec)

    vec_task = asyncio.to_thread(_embed)
    bm25_task = bm25_search_chunk_ids(db, query, limit=k * 2, candidate_pool=200)
    embedding, bm25_ids = await asyncio.gather(vec_task, bm25_task)
    vec_ids = await vector_search_chunk_ids(db, embedding, limit=k * 2)
    return reciprocal_rank_fusion([vec_ids, bm25_ids], top_n=k)


async def rag_search_tool(
    db: AsyncSession,
    query: str,
    *,
    taxpayer_category: str | None,
    retrieval_mode: str = "optimized",
    top_k: int = 8,
) -> tuple[RagSearchObservation, list[DocumentChunk]]:
    """
    Run hybrid (or selected) retrieval over the indexed Ethiopian tax KB.

    The agent receives a small, JSON-safe dict of excerpts; the caller keeps
    the full chunk objects so it can pass them to the final answer step and
    union them into citations.
    """
    chunk_ids = await _retrieve_chunk_ids(
        db, query, mode=retrieval_mode, k=top_k,
        taxpayer_category=taxpayer_category,
    )
    chunks = await load_chunks_by_ids(db, chunk_ids)

    excerpts: list[dict] = []
    for i, ch in enumerate(chunks, start=1):
        meta = ch.chunk_metadata if isinstance(ch.chunk_metadata, dict) else {}
        excerpts.append({
            "i": i,
            "title": (meta.get("document_title") or "Regulation")[:200],
            "proclamation": meta.get("proclamation_number"),
            "article": meta.get("article_number"),
            "text": (ch.content or "").strip()[:600],
        })

    obs = RagSearchObservation(
        query=query,
        chunk_count=len(chunks),
        chunks=excerpts,
        chunk_ids=[str(c.id) for c in chunks],
    )
    logger.info("rag_search_tool query=%r → %d chunks", query[:80], len(chunks))
    return obs, chunks


def _web_search_sync(query: str, *, model: str | None = None) -> WebSearchObservation:
    """
    Blocking implementation: uses Gemini's built-in google_search grounding,
    biased toward Ethiopian sources via the system prompt.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return WebSearchObservation(
            query=query, summary="", citations=[],
            error="GOOGLE_API_KEY missing — web search unavailable",
        )

    from google import genai
    from google.genai import types

    model_id = model or os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    prompt = (
        "You are a research assistant for Ethiopian tax / policy questions. "
        "Use Google Search and PRIORITISE Ethiopian sources — prefer results "
        f"from these domains where relevant: {ETHIOPIAN_SOURCE_HINT}. "
        "Avoid non-Ethiopian sources unless absolutely necessary. "
        "Return a concise factual summary (≤200 words). Do not speculate. "
        "If you cannot find Ethiopian-grounded information, say so explicitly.\n\n"
        f"QUERY: {query.strip()}"
    )

    try:
        response = client.models.generate_content(
            model=model_id, contents=prompt, config=config
        )
    except Exception as exc:
        logger.exception("web_search_failed query=%r", query[:80])
        return WebSearchObservation(query=query, summary="", citations=[], error=str(exc))

    summary = (response.text or "").strip()
    citations: list[dict] = []
    try:
        for cand in response.candidates or []:
            grounding = getattr(cand, "grounding_metadata", None)
            if not grounding:
                continue
            for chunk in getattr(grounding, "grounding_chunks", None) or []:
                web = getattr(chunk, "web", None)
                if web and getattr(web, "uri", None):
                    citations.append({
                        "title": getattr(web, "title", None) or "",
                        "uri": web.uri,
                    })
    except Exception:
        logger.debug("web_search_citation_extract_failed", exc_info=True)

    return WebSearchObservation(query=query, summary=summary, citations=citations[:8])


async def ethiopian_web_search_tool(query: str) -> WebSearchObservation:
    """Async wrapper so the agent loop can await it."""
    return await asyncio.to_thread(_web_search_sync, query)


def gemini_function_declarations():
    """Schemas Gemini needs to know about each tool. Returned as a list of
    ``types.FunctionDeclaration`` so the agent can include them on Tool."""
    from google.genai import types

    return [
        types.FunctionDeclaration(
            name="rag_search",
            description=(
                "Search the internal Awaqi knowledge base of Ethiopian Ministry "
                "of Revenue tax laws, regulations and proclamations. Use this "
                "FIRST and PRIMARILY. Call it multiple times with refined or "
                "translated queries (Amharic ↔ English, narrower terms, "
                "specific article numbers) until you have enough grounded "
                "evidence to answer the user."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A focused search query. Prefer Amharic for tax-law lookups; "
                                       "include keywords like proclamation/article numbers when known.",
                    },
                },
                "required": ["query"],
            },
        ),
        types.FunctionDeclaration(
            name="ethiopian_web_search",
            description=(
                "Search the public web restricted to Ethiopian sources (mor.gov.et, "
                ".et domains, Ethiopian news outlets). Use ONLY when the internal "
                "knowledge base does not contain the answer — e.g. recent news, "
                "circulars, deadlines, or topics not in the indexed regulations. "
                "Never use for general-knowledge questions."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Plain-language web search query.",
                    },
                },
                "required": ["query"],
            },
        ),
    ]
