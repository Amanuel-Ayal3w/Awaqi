"""
RAG evaluation for Awaqi.

This repo previously used RAGAS, but upstream `ragas` imports can break depending
on installed LangChain integrations (e.g. VertexAI). To keep evaluation runnable
in this monorepo, we implement a small, stable evaluator that:

- Uses an LLM judge when `OPENAI_API_KEY` or `GOOGLE_API_KEY` is available.
- Falls back to lightweight lexical heuristics when no API keys are present.

The public API stays compatible with `scripts/evaluate_rag.py`.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class EvaluationResult:
    faithfulness_score: float
    answer_relevancy_score: float
    context_recall_score: float
    context_precision_score: float
    average_score: float


_WORD_RE = re.compile(r"[A-Za-z\u1200-\u137F']+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text or "") if len(t) >= 3}


def _jaccard(a: str, b: str) -> float:
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return float(inter) / float(union) if union else 0.0


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


async def _judge_score(
    *,
    metric: str,
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None,
    model_name: str | None,
) -> float:
    """
    Return a score in [0, 1]. Prefer OpenAI, else Gemini, else heuristic.
    """
    ctx = "\n\n".join(f"[{i+1}] {c.strip()[:1200]}" for i, c in enumerate(contexts[:8]))

    # Offline fallback (keeps local dev / CI runnable)
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        if metric == "answer_relevancy":
            return _clamp01(0.15 + 0.85 * _jaccard(question, answer))
        if metric == "faithfulness":
            return _clamp01(0.10 + 0.90 * _jaccard(answer, ctx))
        if metric == "context_precision":
            if not contexts:
                return 0.0
            per = [_jaccard(question, c) for c in contexts[:8]]
            return _clamp01(sum(per) / max(1, len(per)))
        if metric == "context_recall":
            if not ground_truth:
                return 0.0
            return _clamp01(0.10 + 0.90 * _jaccard(ground_truth, ctx))
        return 0.0

    prompt = (
        "You are evaluating a retrieval-augmented generation (RAG) system.\n"
        "Return ONLY valid JSON: {\"score\": <number between 0 and 1>}.\n"
        "Be strict and consistent.\n\n"
        f"METRIC: {metric}\n"
        "SCORING:\n"
        "- faithfulness: answer is fully supported by CONTEXT; no hallucinated facts.\n"
        "- answer_relevancy: answer directly addresses QUESTION.\n"
        "- context_precision: retrieved CONTEXT passages are relevant to QUESTION.\n"
        "- context_recall: CONTEXT contains the key facts needed to answer GROUND_TRUTH.\n\n"
        f"QUESTION:\n{question.strip()}\n\n"
        f"ANSWER:\n{answer.strip()}\n\n"
        f"GROUND_TRUTH:\n{(ground_truth or '').strip()}\n\n"
        f"CONTEXT:\n{ctx}\n"
    )

    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = model_name or os.getenv("OPENAI_EVAL_MODEL", "gpt-4.1-mini")

        def _call_openai() -> str:
            # Use Responses API when available; fall back to chat.completions if needed.
            try:
                resp = client.responses.create(
                    model=model,
                    input=prompt,
                    temperature=0,
                )
                text = getattr(resp, "output_text", None)
                return (text or "").strip()
            except Exception:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                return (resp.choices[0].message.content or "").strip()

        raw = await asyncio.to_thread(_call_openai)
    else:
        # Gemini is optional; if the dependency isn't installed, fall back to heuristics.
        try:
            from google import genai  # type: ignore[import-not-found]
        except Exception:
            if metric == "answer_relevancy":
                return _clamp01(0.15 + 0.85 * _jaccard(question, answer))
            if metric == "faithfulness":
                return _clamp01(0.10 + 0.90 * _jaccard(answer, ctx))
            if metric == "context_precision":
                if not contexts:
                    return 0.0
                per = [_jaccard(question, c) for c in contexts[:8]]
                return _clamp01(sum(per) / max(1, len(per)))
            if metric == "context_recall":
                if not ground_truth:
                    return 0.0
                return _clamp01(0.10 + 0.90 * _jaccard(ground_truth, ctx))
            return 0.0

        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        model = model_name or os.getenv("GEMINI_EVAL_MODEL", "gemini-2.0-flash")
        client = genai.Client(api_key=api_key)

        def _call_gemini() -> str:
            resp = client.models.generate_content(model=model, contents=prompt)
            return (resp.text or "").strip()

        raw = await asyncio.to_thread(_call_gemini)

    try:
        obj = json.loads(raw)
        return _clamp01(float(obj.get("score", 0.0)))
    except Exception:
        # Last-resort parse: extract first float-like token.
        m = re.search(r"([01](?:\.\d+)?)", raw)
        return _clamp01(float(m.group(1)) if m else 0.0)


async def evaluate_rag(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: Optional[list[str]] = None,
    model_name: str | None = None,
) -> EvaluationResult:
    if len(questions) != len(answers) or len(questions) != len(contexts):
        raise ValueError("questions, answers, contexts must be same length")

    gts = ground_truths or [None] * len(questions)
    if ground_truths and len(ground_truths) != len(questions):
        raise ValueError("ground_truths must be same length as questions (or None)")

    async def _score_one(i: int) -> tuple[float, float, float, float]:
        q = questions[i]
        a = answers[i]
        c = contexts[i] or []
        gt = gts[i]
        faith = await _judge_score(
            metric="faithfulness",
            question=q,
            answer=a,
            contexts=c,
            ground_truth=gt,
            model_name=model_name,
        )
        rel = await _judge_score(
            metric="answer_relevancy",
            question=q,
            answer=a,
            contexts=c,
            ground_truth=gt,
            model_name=model_name,
        )
        crecall = await _judge_score(
            metric="context_recall",
            question=q,
            answer=a,
            contexts=c,
            ground_truth=gt,
            model_name=model_name,
        )
        cprec = await _judge_score(
            metric="context_precision",
            question=q,
            answer=a,
            contexts=c,
            ground_truth=gt,
            model_name=model_name,
        )
        return faith, rel, crecall, cprec

    rows = await asyncio.gather(*[_score_one(i) for i in range(len(questions))])
    if not rows:
        return EvaluationResult(0.0, 0.0, 0.0, 0.0, 0.0)

    faithfulness_avg = sum(r[0] for r in rows) / len(rows)
    answer_relevancy_avg = sum(r[1] for r in rows) / len(rows)
    context_recall_avg = sum(r[2] for r in rows) / len(rows)
    context_precision_avg = sum(r[3] for r in rows) / len(rows)
    overall_avg = (
        faithfulness_avg + answer_relevancy_avg + context_recall_avg + context_precision_avg
    ) / 4.0

    return EvaluationResult(
        faithfulness_score=float(faithfulness_avg),
        answer_relevancy_score=float(answer_relevancy_avg),
        context_recall_score=float(context_recall_avg),
        context_precision_score=float(context_precision_avg),
        average_score=float(overall_avg),
    )


def evaluate_rag_sync(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: Optional[list[str]] = None,
    model_name: str | None = None,
) -> EvaluationResult:
    return asyncio.run(
        evaluate_rag(
            questions=questions,
            answers=answers,
            contexts=contexts,
            ground_truths=ground_truths,
            model_name=model_name,
        )
    )
