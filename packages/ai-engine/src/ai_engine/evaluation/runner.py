"""
End-to-end evaluation runner.

For each benchmark item:
  1. retrieve top-k chunks under the selected retrieval mode
  2. mark each as relevant if its document's proclamation_number matches
     the ground-truth proclamation_number (case-insensitive substring match)
  3. generate the RAG answer with the existing pipeline
  4. compute retrieval metrics + LLM-as-judge + semantic similarity
  5. persist a JSON run file under data/evaluations/runs/

Retrieval modes:
  - ``optimized``  hybrid (vector + BM25) + NLU query bias  (current production)
  - ``dense_only`` vector-only — simulates "no keyword search"
  - ``bm25_only``  BM25-only  — simulates "no Amharic-optimized embedding"
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.document import Document, DocumentChunk

from ai_engine.agent.react_agent import run_awaqi_max
from ai_engine.agent.tools import _retrieve_chunk_ids as _agent_retrieve_chunk_ids
from ai_engine.embeddings import embed_query_sync
from ai_engine.evaluation.dataset import BenchmarkItem
from ai_engine.evaluation.judge import judge_answer
from ai_engine.evaluation.metrics import (
    cosine_similarity,
    hit_at_k,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from ai_engine.hybrid_retrieval import load_chunks_by_ids
from ai_engine.rag_answer import answer_from_chunks

logger = logging.getLogger(__name__)

RetrievalMode = Literal["optimized", "dense_only", "bm25_only"]
AssistantMode = Literal["basic", "awaqi_max"]
DEFAULT_K = 10


@dataclass
class PerItemResult:
    item_id: str
    question: str
    expected_answer: str
    actual_answer: str
    language: str
    topic: str
    latency_ms: float
    retrieved_chunk_ids: list[str]
    retrieved_doc_ids: list[str]
    retrieved_proclamations: list[str | None]
    relevant_mask: list[bool]
    hit_at_k: float
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    semantic_similarity: float
    judge_faithfulness: float
    judge_answer_relevance: float
    judge_context_recall: float
    judge_correctness: float
    judge_overall: float
    judge_rationale: str
    citations: list[dict] = field(default_factory=list)
    # Awaqi Max only — number of tool calls + presence of web grounding
    agent_tool_calls: int = 0
    agent_used_web_search: bool = False


@dataclass
class RunSummary:
    run_id: str
    mode: RetrievalMode
    assistant_mode: AssistantMode
    k: int
    started_at: str
    finished_at: str
    total_questions: int
    avg_latency_ms: float
    avg_hit_at_k: float
    avg_precision_at_k: float
    avg_recall_at_k: float
    avg_mrr: float
    avg_ndcg_at_k: float
    avg_semantic_similarity: float
    avg_judge_faithfulness: float
    avg_judge_answer_relevance: float
    avg_judge_context_recall: float
    avg_judge_correctness: float
    avg_judge_overall: float
    avg_agent_tool_calls: float = 0.0
    pct_agent_used_web_search: float = 0.0


def _norm(text_value: str | None) -> str:
    return (text_value or "").strip().lower()


def _proclamation_matches(retrieved: str | None, expected: str | None) -> bool:
    """
    Loose match: "410/2017" ≈ "410/2009" if the leading number agrees,
    plus a direct substring fallback. The Amharic regulations are often
    referenced by the proclamation number alone (e.g. "410").
    """
    r, e = _norm(retrieved), _norm(expected)
    if not r or not e:
        return False
    if r == e or r in e or e in r:
        return True
    r_lead = r.split("/")[0].strip()
    e_lead = e.split("/")[0].strip()
    return bool(r_lead) and r_lead == e_lead


async def _retrieve_chunk_ids(
    db: AsyncSession,
    query: str,
    *,
    mode: RetrievalMode,
    k: int,
) -> list[uuid.UUID]:
    return await _agent_retrieve_chunk_ids(
        db, query, mode=mode, k=k, taxpayer_category=None
    )


async def _load_chunk_doc_metadata(
    db: AsyncSession, chunk_ids: list[uuid.UUID]
) -> tuple[list[DocumentChunk], dict[uuid.UUID, Document]]:
    if not chunk_ids:
        return [], {}
    chunks = await load_chunks_by_ids(db, chunk_ids)
    doc_ids = {c.document_id for c in chunks}
    if not doc_ids:
        return chunks, {}
    res = await db.execute(select(Document).where(Document.id.in_(doc_ids)))
    docs = {d.id: d for d in res.scalars().all()}
    return chunks, docs


def _semantic_similarity(expected: str, actual: str) -> float:
    if not expected.strip() or not actual.strip():
        return 0.0
    try:
        e_vec = embed_query_sync(expected)
        a_vec = embed_query_sync(actual)
    except Exception:
        logger.exception("semantic_similarity_embed_failed")
        return 0.0
    return cosine_similarity(e_vec, a_vec)


async def evaluate_item(
    db: AsyncSession,
    item: BenchmarkItem,
    *,
    mode: RetrievalMode,
    assistant_mode: AssistantMode,
    k: int,
    use_judge: bool,
    use_semantic_sim: bool,
) -> PerItemResult:
    start = time.perf_counter()
    agent_tool_calls = 0
    agent_used_web_search = False
    citation_dicts: list[dict]
    answer_text: str

    if assistant_mode == "awaqi_max":
        # Let the ReAct agent drive retrieval. Score against the UNION of all
        # chunks the agent surfaced across its tool calls.
        agent_result = await run_awaqi_max(
            db, item.question,
            language=item.language,
            taxpayer_category=None,
            retrieval_mode=mode,
        )
        chunks = agent_result.chunks
        answer_text = agent_result.answer
        citation_dicts = agent_result.citations
        for step in agent_result.trace:
            if step.type == "tool_call":
                agent_tool_calls += 1
                if step.tool_name == "ethiopian_web_search":
                    agent_used_web_search = True
    else:
        chunk_ids = await _retrieve_chunk_ids(db, item.question, mode=mode, k=k)
        chunks = (await _load_chunk_doc_metadata(db, chunk_ids))[0]
        answer_text, citation_dicts, _conf, _follow = await answer_from_chunks(
            item.question, chunks, language=item.language
        )

    # Always look up doc metadata so we can score retrieval against ground truth
    chunks_with_meta, docs = await _load_chunk_doc_metadata(
        db, [c.id for c in chunks]
    )
    chunks = chunks_with_meta or chunks
    retrieve_ms = (time.perf_counter() - start) * 1000.0

    retrieved_proclamations: list[str | None] = []
    relevant_mask: list[bool] = []
    expected_proc = item.ground_truth.proclamation_number
    for ch in chunks:
        doc = docs.get(ch.document_id)
        proc = doc.proclamation_number if doc else None
        # fall back to chunk metadata when the document row didn't carry it
        if not proc and isinstance(ch.chunk_metadata, dict):
            proc = ch.chunk_metadata.get("proclamation_number")
        retrieved_proclamations.append(proc)
        relevant_mask.append(_proclamation_matches(proc, expected_proc))

    total_ms = (time.perf_counter() - start) * 1000.0
    logger.info(
        "eval_item id=%s mode=%s asst=%s retrieve_ms=%.1f total_ms=%.1f hits=%d/%d",
        item.id, mode, assistant_mode, retrieve_ms, total_ms,
        sum(relevant_mask), len(relevant_mask),
    )

    p_at_k = precision_at_k(relevant_mask, k)
    r_at_k = recall_at_k(relevant_mask, k, total_relevant=sum(relevant_mask))
    h_at_k = hit_at_k(relevant_mask, k)
    rr = mrr(relevant_mask)
    nd = ndcg_at_k(relevant_mask, k)

    sem_sim = 0.0
    if use_semantic_sim:
        sem_sim = _semantic_similarity(item.expected_answer, answer_text)

    if use_judge:
        passages = [(ch.content or "")[:1200] for ch in chunks[:6]]
        judge = judge_answer(
            question=item.question,
            expected_answer=item.expected_answer,
            actual_answer=answer_text,
            context_passages=passages,
        )
    else:
        from ai_engine.evaluation.judge import JudgeScore
        judge = JudgeScore(0, 0, 0, 0, 0, "judge disabled")

    return PerItemResult(
        item_id=item.id,
        question=item.question,
        expected_answer=item.expected_answer,
        actual_answer=answer_text,
        language=item.language,
        topic=item.topic,
        latency_ms=total_ms,
        retrieved_chunk_ids=[str(c.id) for c in chunks],
        retrieved_doc_ids=[str(c.document_id) for c in chunks],
        retrieved_proclamations=retrieved_proclamations,
        relevant_mask=relevant_mask,
        hit_at_k=h_at_k,
        precision_at_k=p_at_k,
        recall_at_k=r_at_k,
        mrr=rr,
        ndcg_at_k=nd,
        semantic_similarity=sem_sim,
        judge_faithfulness=judge.faithfulness,
        judge_answer_relevance=judge.answer_relevance,
        judge_context_recall=judge.context_recall,
        judge_correctness=judge.correctness,
        judge_overall=judge.overall,
        judge_rationale=judge.rationale,
        citations=citation_dicts,
        agent_tool_calls=agent_tool_calls,
        agent_used_web_search=agent_used_web_search,
    )


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarise(run_id: str, mode: RetrievalMode, assistant_mode: AssistantMode,
              k: int, started_at: str,
              results: list[PerItemResult]) -> RunSummary:
    web_uses = sum(1 for r in results if r.agent_used_web_search)
    return RunSummary(
        run_id=run_id,
        mode=mode,
        assistant_mode=assistant_mode,
        k=k,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(),
        total_questions=len(results),
        avg_latency_ms=_avg([r.latency_ms for r in results]),
        avg_hit_at_k=_avg([r.hit_at_k for r in results]),
        avg_precision_at_k=_avg([r.precision_at_k for r in results]),
        avg_recall_at_k=_avg([r.recall_at_k for r in results]),
        avg_mrr=_avg([r.mrr for r in results]),
        avg_ndcg_at_k=_avg([r.ndcg_at_k for r in results]),
        avg_semantic_similarity=_avg([r.semantic_similarity for r in results]),
        avg_judge_faithfulness=_avg([r.judge_faithfulness for r in results]),
        avg_judge_answer_relevance=_avg([r.judge_answer_relevance for r in results]),
        avg_judge_context_recall=_avg([r.judge_context_recall for r in results]),
        avg_judge_correctness=_avg([r.judge_correctness for r in results]),
        avg_judge_overall=_avg([r.judge_overall for r in results]),
        avg_agent_tool_calls=_avg([float(r.agent_tool_calls) for r in results]),
        pct_agent_used_web_search=(web_uses / len(results)) if results else 0.0,
    )


def save_run(
    output_dir: str | Path,
    summary: RunSummary,
    results: list[PerItemResult],
    *,
    benchmark_name: str,
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "benchmark": benchmark_name,
        "summary": asdict(summary),
        "results": [asdict(r) for r in results],
    }
    file_path = out / f"{summary.run_id}.json"
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return file_path


async def run_evaluation(
    db: AsyncSession,
    items: list[BenchmarkItem],
    *,
    mode: RetrievalMode = "optimized",
    assistant_mode: AssistantMode = "basic",
    k: int = DEFAULT_K,
    use_judge: bool = True,
    use_semantic_sim: bool = True,
    run_id: str | None = None,
) -> tuple[RunSummary, list[PerItemResult]]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = run_id or f"{assistant_mode}-{mode}-{timestamp}"
    started_at = datetime.now(timezone.utc).isoformat()
    results: list[PerItemResult] = []
    for i, item in enumerate(items, start=1):
        logger.info(
            "eval_progress %d/%d id=%s mode=%s asst=%s",
            i, len(items), item.id, mode, assistant_mode,
        )
        try:
            result = await evaluate_item(
                db, item,
                mode=mode,
                assistant_mode=assistant_mode,
                k=k,
                use_judge=use_judge,
                use_semantic_sim=use_semantic_sim,
            )
        except Exception:
            logger.exception("eval_item_failed id=%s", item.id)
            continue
        results.append(result)
    summary = summarise(run_id, mode, assistant_mode, k, started_at, results)
    return summary, results
