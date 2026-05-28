"""
Awaqi Max — ReAct agent loop on top of Gemini function calling.

Loop shape (Reason → Act → Observe):
  1. Gemini sees the user question + tool schemas and decides whether to call
     a tool (rag_search / ethiopian_web_search) or to answer directly.
  2. If it calls a tool, we execute it and append the FunctionResponse.
  3. Repeat until either:
       - Gemini returns text (the final answer), or
       - we hit MAX_ITERATIONS.

Output to the caller:
  - the final answer text,
  - the merged citation list (KB + Ethiopian web grounding),
  - the union of all DocumentChunks the agent retrieved (so the existing
    cited_chunks JSON storage stays consistent with basic mode),
  - a trace of every tool call (for /admin/evaluation drill-down).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from database.models.document import DocumentChunk
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.agent.tools import (
    ETHIOPIAN_SOURCE_HINT,
    ethiopian_web_search_tool,
    gemini_function_declarations,
    rag_search_tool,
)
from ai_engine.rag_answer import chunks_to_citations, estimate_confidence

logger = logging.getLogger(__name__)

MAX_ITERATIONS = int(os.getenv("AWAQI_MAX_ITERATIONS", "5"))
RAG_TOP_K = int(os.getenv("AWAQI_MAX_RAG_TOP_K", "8"))


@dataclass
class AgentTrace:
    """One Reason → Act → Observe step (or final answer)."""

    step: int
    type: str  # "tool_call" | "final_answer" | "error"
    tool_name: str | None = None
    tool_args: dict | None = None
    observation: dict | None = None
    text: str | None = None


@dataclass
class AgentResult:
    answer: str
    citations: list[dict]
    confidence: float
    chunks: list[DocumentChunk] = field(default_factory=list)
    trace: list[AgentTrace] = field(default_factory=list)
    web_citations: list[dict] = field(default_factory=list)


SYSTEM_INSTRUCTIONS = (
    "You are Awaqi Max — an agentic assistant for Ethiopian Ministry of Revenue "
    "tax laws and proclamations. Follow this loop strictly:\n"
    "1. Decide: do you need more evidence?\n"
    "2. If yes, call `rag_search` with a focused query. Prefer Amharic for "
    "   regulation lookups; include proclamation/article numbers if known.\n"
    "3. If the KB does not have it, then — and ONLY then — call "
    "   `ethiopian_web_search` (which is restricted to Ethiopian sources: "
    f"   {ETHIOPIAN_SOURCE_HINT}).\n"
    "4. You may call tools up to "
    f"   {MAX_ITERATIONS} times. Refine queries if the first attempt is empty.\n"
    "5. When you have enough grounded evidence, write the FINAL ANSWER:\n"
    "   - In the user's preferred language.\n"
    "   - Use ONLY facts present in the tool observations. If evidence is "
    "     insufficient, say so explicitly — do not speculate.\n"
    "   - Add inline citation markers like [1] [2] matching the order in "
    "     which the supporting KB excerpts appeared in your observations.\n"
    "   - Keep it concise and direct.\n"
)


def _build_user_prompt(user_query: str, language: str) -> str:
    lang_hint = "Amharic" if language == "am" else "English" if language == "en" else "the user's language"
    return (
        f"USER LANGUAGE: {lang_hint}\n"
        f"USER QUESTION: {user_query.strip()}"
    )


def _format_function_response(name: str, payload: dict) -> Any:
    """Build a Gemini FunctionResponse content part."""
    from google.genai import types
    return types.Part.from_function_response(name=name, response=payload)


def _extract_function_call(response) -> tuple[str, dict] | None:
    for cand in response.candidates or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if fc and getattr(fc, "name", None):
                args_raw = getattr(fc, "args", None) or {}
                # ``args`` arrives as a protobuf-ish mapping; coerce to plain dict
                try:
                    args = dict(args_raw)
                except Exception:
                    args = {}
                return fc.name, args
    return None


def _extract_text(response) -> str:
    text = (getattr(response, "text", None) or "").strip()
    if text:
        return text
    parts_text: list[str] = []
    for cand in response.candidates or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "text", None):
                parts_text.append(part.text)
    return "\n".join(parts_text).strip()


async def run_awaqi_max(
    db: AsyncSession,
    user_query: str,
    *,
    language: str,
    taxpayer_category: str | None,
    retrieval_mode: str = "optimized",
) -> AgentResult:
    """
    Drive the ReAct loop. Falls back to a plain text response if no
    GOOGLE_API_KEY is set so local development is still usable.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        logger.warning("awaqi_max_unavailable reason=missing_GOOGLE_API_KEY")
        return AgentResult(
            answer=(
                "Awaqi Max is unavailable (GOOGLE_API_KEY is not configured). "
                "Falling back to basic mode is recommended."
            ),
            citations=[],
            confidence=0.0,
        )

    from google import genai
    from google.genai import types

    model_id = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTIONS,
        tools=[types.Tool(function_declarations=gemini_function_declarations())],
    )

    contents: list[Any] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=_build_user_prompt(user_query, language))],
        ),
    ]

    trace: list[AgentTrace] = []
    all_chunks: dict[str, DocumentChunk] = {}
    web_citations: list[dict] = []

    for step in range(1, MAX_ITERATIONS + 1):
        try:
            response = await _generate_async(client, model_id, contents, config)
        except Exception as exc:
            logger.exception("awaqi_max_gemini_error step=%d", step)
            trace.append(AgentTrace(step=step, type="error", text=str(exc)))
            return AgentResult(
                answer="The agent encountered an error. Please retry or use basic mode.",
                citations=[],
                confidence=0.0,
                trace=trace,
            )

        call = _extract_function_call(response)
        if call is None:
            final_text = _extract_text(response) or (
                "I could not produce a grounded answer. Try rephrasing your question."
            )
            trace.append(AgentTrace(step=step, type="final_answer", text=final_text))
            merged_chunks = list(all_chunks.values())
            citations = chunks_to_citations(merged_chunks)
            for wc in web_citations:
                citations.append({
                    "source": (wc.get("title") or wc.get("uri") or "Web")[:512],
                    "page": 0,
                    "text": wc.get("uri") or "",
                    "document_title": wc.get("title"),
                    "proclamation_number": None,
                    "article_number": None,
                })
            return AgentResult(
                answer=final_text,
                citations=citations,
                confidence=estimate_confidence(merged_chunks),
                chunks=merged_chunks,
                trace=trace,
                web_citations=web_citations,
            )

        tool_name, tool_args = call
        # Persist the model turn so the next request includes its function_call
        contents.append(_first_candidate_content(response))

        if tool_name == "rag_search":
            query = str(tool_args.get("query", "")).strip() or user_query
            obs, chunks = await rag_search_tool(
                db, query,
                taxpayer_category=taxpayer_category,
                retrieval_mode=retrieval_mode,
                top_k=RAG_TOP_K,
            )
            for ch in chunks:
                all_chunks.setdefault(str(ch.id), ch)
            trace.append(AgentTrace(
                step=step, type="tool_call", tool_name=tool_name,
                tool_args={"query": query}, observation=obs.to_agent_dict(),
            ))
            contents.append(types.Content(
                role="tool",
                parts=[_format_function_response("rag_search", obs.to_agent_dict())],
            ))
            continue

        if tool_name == "ethiopian_web_search":
            query = str(tool_args.get("query", "")).strip() or user_query
            web_obs = await ethiopian_web_search_tool(query)
            for cite in web_obs.citations:
                web_citations.append(cite)
            trace.append(AgentTrace(
                step=step, type="tool_call", tool_name=tool_name,
                tool_args={"query": query}, observation=web_obs.to_agent_dict(),
            ))
            contents.append(types.Content(
                role="tool",
                parts=[_format_function_response("ethiopian_web_search", web_obs.to_agent_dict())],
            ))
            continue

        # Unknown tool name from the model — log and force termination
        logger.warning("awaqi_max_unknown_tool name=%r", tool_name)
        trace.append(AgentTrace(
            step=step, type="error",
            text=f"Unknown tool: {tool_name}",
        ))
        break

    # Hit max iterations without a final answer — synthesize one from collected evidence
    logger.info("awaqi_max_max_iterations_reached chunks=%d", len(all_chunks))
    merged_chunks = list(all_chunks.values())
    if not merged_chunks:
        return AgentResult(
            answer="I could not find enough evidence within the iteration budget.",
            citations=[],
            confidence=0.0,
            trace=trace,
        )

    from ai_engine.rag_answer import answer_from_chunks
    text, citation_dicts, conf, _ = await answer_from_chunks(
        user_query, merged_chunks, language=language,
    )
    for wc in web_citations:
        citation_dicts.append({
            "source": (wc.get("title") or wc.get("uri") or "Web")[:512],
            "page": 0,
            "text": wc.get("uri") or "",
            "document_title": wc.get("title"),
            "proclamation_number": None,
            "article_number": None,
        })
    trace.append(AgentTrace(step=MAX_ITERATIONS + 1, type="final_answer", text=text))
    return AgentResult(
        answer=text,
        citations=citation_dicts,
        confidence=conf,
        chunks=merged_chunks,
        trace=trace,
        web_citations=web_citations,
    )


def _first_candidate_content(response):
    for cand in response.candidates or []:
        if getattr(cand, "content", None):
            return cand.content
    # Defensive fallback so the next call doesn't crash
    from google.genai import types
    return types.Content(role="model", parts=[types.Part.from_text(text="")])


async def _generate_async(client, model_id: str, contents, config):
    """Run Gemini generate_content off the event loop."""
    import asyncio
    return await asyncio.to_thread(
        client.models.generate_content,
        model=model_id, contents=contents, config=config,
    )


def trace_to_json(trace: list[AgentTrace]) -> list[dict]:
    """Helper for the chat route: JSON-safe serialisation of the agent trace."""
    out: list[dict] = []
    for step in trace:
        item: dict[str, Any] = {"step": step.step, "type": step.type}
        if step.tool_name:
            item["tool_name"] = step.tool_name
        if step.tool_args is not None:
            item["tool_args"] = step.tool_args
        if step.observation is not None:
            # Keep payload small (drop full chunk excerpts here — they're in citations)
            obs = dict(step.observation)
            if "chunks" in obs and isinstance(obs["chunks"], list):
                obs["chunks"] = [
                    {k: v for k, v in c.items() if k != "text"} for c in obs["chunks"]
                ]
            item["observation"] = obs
        if step.text is not None:
            item["text"] = step.text[:600]
        out.append(item)
    return out


# Re-export so callers can do ``from ai_engine.agent.react_agent import ...``
__all__ = ["AgentResult", "AgentTrace", "run_awaqi_max", "trace_to_json"]
