"""
RAG answer synthesis with mandatory citations (AWA-27 groundwork).

Uses Gemini Flash (``GOOGLE_API_KEY``) for answer generation; falls back to a
deterministic extractive summary so local dev still returns grounded text.
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import partial
from typing import Any

from database.models.document import DocumentChunk

logger = logging.getLogger(__name__)


def _chunk_meta_page(meta: dict[str, Any] | None) -> int:
    if not meta:
        return 1
    pages = meta.get("pages")
    if isinstance(pages, list) and pages:
        try:
            return int(pages[0])
        except (TypeError, ValueError):
            return 1
    return 1


def chunks_to_citations(chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ch in chunks[:8]:
        meta = ch.chunk_metadata if isinstance(ch.chunk_metadata, dict) else {}
        title = (meta.get("document_title") or meta.get("source_url") or "Regulation")[:512]
        excerpt = (ch.content or "").strip()[:600]
        out.append(
            {
                "source": str(title),
                "page": _chunk_meta_page(meta),
                "text": excerpt or "(empty excerpt)",
                "document_title": meta.get("document_title"),
                "proclamation_number": meta.get("proclamation_number") or None,
                "article_number": meta.get("article_number") or None,
            }
        )
    return out


def _extractive_answer(user_query: str, chunks: list[DocumentChunk]) -> str:
    if not chunks:
        return (
            "I could not find matching regulations in the knowledge base yet. "
            "Try rephrasing, or check that documents have been indexed."
        )
    lines = [
        "Below are the closest passages from the indexed regulations (not a full legal opinion):"
    ]
    for i, ch in enumerate(chunks[:5], start=1):
        excerpt = (ch.content or "").strip().replace("\n", " ")[:320]
        lines.append(f"[{i}] {excerpt}…")
    lines.append("")
    lines.append(f"Your question was: {user_query.strip()}")
    return "\n".join(lines)


def _generate_gemini_sync(
    user_query: str, context: str, language: str, chunks: list[DocumentChunk]
) -> str:
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY missing")
    model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)
    prompt = (
        "You are Awaqi, an assistant for Ethiopian tax and Ministry of Revenue materials. "
        f"Preferred answer language hint: {language}. "
        "Answer ONLY using the numbered passages in CONTEXT. After each sentence that uses a passage, "
        "add a citation marker like [1] matching the passage number. "
        "If CONTEXT is insufficient, say so briefly.\n\n"
        f"CONTEXT:\n{context}\n\nQUESTION:\n{user_query.strip()}"
    )
    response = client.models.generate_content(model=model, contents=prompt)
    text = (response.text or "").strip()
    if not text:
        return _extractive_answer(user_query, chunks)
    return text


def estimate_confidence(chunks: list[DocumentChunk]) -> float:
    if not chunks:
        return 0.0
    # Simple monotonic score: more agreeing chunks → higher (capped)
    return min(0.9, 0.35 + 0.1 * min(len(chunks), 5))


def _generate_follow_ups_sync(
    user_query: str, response_text: str, language: str
) -> list[str]:
    import json

    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return []
    model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)
    lang_hint = "Amharic" if language == "am" else "English"
    prompt = (
        f"You are an Ethiopian tax assistant. Given the Q&A below, suggest exactly 3 short follow-up "
        f"questions a taxpayer might naturally ask next. Respond in {lang_hint}. "
        "Return ONLY a JSON array of 3 strings — no markdown, no explanation.\n\n"
        f"Q: {user_query.strip()[:300]}\n"
        f"A: {response_text.strip()[:500]}"
    )
    try:
        resp = client.models.generate_content(model=model, contents=prompt)
        text = (resp.text or "").strip()
        # Strip markdown code fences if the model wrapped the JSON
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        chips = json.loads(text)
        if isinstance(chips, list):
            return [str(c).strip() for c in chips[:3] if c and str(c).strip()]
    except Exception:
        logger.debug("follow_up_generation_failed", exc_info=True)
    return []


async def answer_from_chunks(
    user_query: str,
    chunks: list[DocumentChunk],
    *,
    language: str,
) -> tuple[str, list[dict[str, Any]], float, list[str]]:
    citations = chunks_to_citations(chunks)
    if not chunks:
        return (
            "I could not find matching regulations in the knowledge base yet. "
            "Try different wording or ask an admin to upload or scrape documents.",
            [],
            0.0,
            [],
        )

    ctx_lines = []
    for i, ch in enumerate(chunks[:6], start=1):
        ctx_lines.append(f"[{i}] {(ch.content or '').strip()[:1200]}")
    context = "\n\n".join(ctx_lines)

    lang = language or "en"
    if os.getenv("GOOGLE_API_KEY"):
        try:
            text = await asyncio.to_thread(
                partial(_generate_gemini_sync, chunks=chunks),
                user_query,
                context,
                lang,
            )
            follow_ups = await asyncio.to_thread(
                _generate_follow_ups_sync, user_query, text, lang
            )
            return text, citations, estimate_confidence(chunks), follow_ups
        except Exception:
            logger.exception("gemini_chat_failed falling back to extractive")
    text = _extractive_answer(user_query, chunks)
    return text, citations, estimate_confidence(chunks), []
