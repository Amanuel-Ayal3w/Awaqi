"""
RAG answer synthesis with mandatory citations and document-lifecycle awareness.

Each retrieved passage is labelled with its legal enforcement status
(CURRENTLY IN EFFECT vs DRAFT — NOT YET IN EFFECT) so the LLM can
clearly distinguish binding law from forthcoming/proposed rules and
surface that distinction to the taxpayer in every answer.
"""

from __future__ import annotations

import asyncio
import logging
import os
from functools import partial
from typing import Any

from database.models.document import DocumentChunk

logger = logging.getLogger(__name__)

# ── Enforcement-status helpers ─────────────────────────────────────────────────

_STATUS_LABEL: dict[str, str] = {
    "in_effect": "CURRENTLY IN EFFECT",
    "draft": "DRAFT — NOT YET IN EFFECT",
}


def _enforcement_label(meta: dict[str, Any] | None) -> str:
    raw = (meta or {}).get("enforcement_status", "in_effect")
    return _STATUS_LABEL.get(str(raw), "CURRENTLY IN EFFECT")


# ── Citation helpers ───────────────────────────────────────────────────────────


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
                "enforcement_status": meta.get("enforcement_status", "in_effect"),
            }
        )
    return out


# ── Fallback extractive answer ─────────────────────────────────────────────────


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
        meta = ch.chunk_metadata if isinstance(ch.chunk_metadata, dict) else {}
        label = _enforcement_label(meta)
        excerpt = (ch.content or "").strip().replace("\n", " ")[:320]
        lines.append(f"[{i}] [{label}] {excerpt}…")
    lines.append("")
    lines.append(f"Your question was: {user_query.strip()}")
    return "\n".join(lines)


# ── Gemini generation ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are Awaqi (አዋቂ), the official AI assistant for Ethiopian tax law and \
Ministry of Revenue (MoR) regulations.

LANGUAGE RULE — CRITICAL:
Respond ENTIRELY in the same language the user wrote their question in.
• If the question is in Amharic → answer in Amharic.
• If the question is in English → answer in English.
• If the question mixes both → match the dominant language and include \
key terms in the other language in parentheses where helpful.
Never switch language mid-answer without a clear reason.

DOCUMENT STATUS RULE — CRITICAL:
Every passage in CONTEXT carries a status tag: \
[CURRENTLY IN EFFECT] or [DRAFT — NOT YET IN EFFECT].
• Treat passages tagged [CURRENTLY IN EFFECT] as binding law. \
Cite them first and present their content as current obligations.
• Treat passages tagged [DRAFT — NOT YET IN EFFECT] as proposed or \
forthcoming rules. When you use them, ALWAYS explicitly warn the taxpayer \
that this rule has NOT yet taken effect and may still change.
• If both types exist for the same topic, first explain the current rule, \
then describe what the draft proposes to change.
• NEVER present a DRAFT rule as currently binding law.

ANSWER QUALITY RULES:
1. Answer ONLY using the numbered passages in CONTEXT. \
After every sentence that draws on a passage add a citation marker \
like [1] that matches the passage number.
2. Be comprehensive: cover obligations, deadlines, rates, exemptions, \
and penalties where the context contains them.
3. Use Markdown formatting to make the answer scannable:
   • Use **bold** for key terms, rates, and deadlines.
   • Use tables (| col | col |) to compare multiple items, rate brackets, \
or periods side-by-side.
   • Use bullet or numbered lists for multi-step procedures.
   • Use a ⚠️ callout block (> ⚠️ …) for draft-status warnings.
4. End with a short "Summary" section that recaps the key takeaway \
in 1–2 sentences.
5. If CONTEXT is insufficient to answer fully, say so clearly and \
suggest which kind of document the user should consult.
"""


def _build_context_block(chunks: list[DocumentChunk]) -> str:
    lines: list[str] = []
    for i, ch in enumerate(chunks[:6], start=1):
        meta = ch.chunk_metadata if isinstance(ch.chunk_metadata, dict) else {}
        label = _enforcement_label(meta)
        doc_title = (meta.get("document_title") or "Regulation")[:80]
        proc_no = meta.get("proclamation_number", "")
        header_parts = [f"[{label}]", doc_title]
        if proc_no:
            header_parts.append(f"Proc. No. {proc_no}")
        header = " | ".join(header_parts)
        content = (ch.content or "").strip()[:1200]
        lines.append(f"[{i}] {header}\n{content}")
    return "\n\n".join(lines)


def _generate_gemini_sync(
    user_query: str, context: str, language: str, chunks: list[DocumentChunk]
) -> str:
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY missing")
    model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)

    lang_hint = "am" if language == "am" else language or "en"
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"(Session language hint: {lang_hint})\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{user_query.strip()}"
    )
    response = client.models.generate_content(model=model, contents=prompt)
    text = (response.text or "").strip()
    if not text:
        return _extractive_answer(user_query, chunks)
    return text


# ── Confidence estimation ──────────────────────────────────────────────────────


def estimate_confidence(chunks: list[DocumentChunk]) -> float:
    if not chunks:
        return 0.0
    return min(0.9, 0.35 + 0.1 * min(len(chunks), 5))


# ── Follow-up suggestions ──────────────────────────────────────────────────────


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
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        chips = json.loads(text)
        if isinstance(chips, list):
            return [str(c).strip() for c in chips[:3] if c and str(c).strip()]
    except Exception:
        logger.debug("follow_up_generation_failed", exc_info=True)
    return []


# ── Public entry point ─────────────────────────────────────────────────────────


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

    context = _build_context_block(chunks)
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
