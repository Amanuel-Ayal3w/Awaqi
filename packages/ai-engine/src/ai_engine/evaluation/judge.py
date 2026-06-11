"""
LLM-as-judge scoring for RAG answers using Gemini.

Rubric (each 1..10):
  - faithfulness          — is the answer grounded in the retrieved context?
  - answer_relevance      — does the answer address the question?
  - context_recall        — did retrieval surface the facts needed for the expected answer?
  - correctness           — does the answer match the expected/ground-truth answer?
  - overall               — weighted aggregate (1..10)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)


@dataclass
class JudgeScore:
    faithfulness: float
    answer_relevance: float
    context_recall: float
    correctness: float
    overall: float
    rationale: str

    def as_dict(self) -> dict:
        return asdict(self)


_JUDGE_PROMPT = """You are an impartial grader for an Ethiopian tax assistant.
Score the candidate answer on a 1..10 integer scale across four axes.

QUESTION:
{question}

EXPECTED ANSWER (ground truth from the official regulation):
{expected}

RETRIEVED CONTEXT PASSAGES (numbered):
{context}

CANDIDATE ANSWER (from the system under test):
{actual}

Scoring rubric (1 = poor, 10 = perfect):
  - faithfulness: Is every factual claim in the candidate supported by the retrieved context?
                  Penalise hallucinations (claims not in context). Ignore citation markers.
  - answer_relevance: Does the candidate directly address what the question asks?
                  Penalise off-topic content and verbose tangents.
  - context_recall: Do the retrieved passages contain the key facts needed to produce the
                  expected answer? Score what the RETRIEVED PASSAGES contain, not the candidate.
  - correctness: How closely does the candidate match the expected answer in substance?
                  Numbers, article references, and conditions must match. Wording may differ.

Then compute "overall" = round(0.30*correctness + 0.30*faithfulness +
                                0.20*answer_relevance + 0.20*context_recall).

Return ONLY a JSON object (no markdown, no commentary) with EXACTLY these keys:
{{
  "faithfulness": <int 1-10>,
  "answer_relevance": <int 1-10>,
  "context_recall": <int 1-10>,
  "correctness": <int 1-10>,
  "overall": <int 1-10>,
  "rationale": "<one short sentence>"
}}"""


def _clamp(value: float, lo: float = 1.0, hi: float = 10.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines[-1].strip().startswith("```"):
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        t = "\n".join(lines).strip()
    return t


def _parse_json_payload(text: str) -> dict | None:
    t = _strip_code_fence(text)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", t, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def judge_answer(
    *,
    question: str,
    expected_answer: str,
    actual_answer: str,
    context_passages: list[str],
    model: str | None = None,
) -> JudgeScore:
    """
    Score one Q/A pair. Returns zeros if the LLM is unavailable so the rest
    of the eval run still completes.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        logger.warning("judge_skipped reason=missing_GOOGLE_API_KEY")
        return JudgeScore(0.0, 0.0, 0.0, 0.0, 0.0, "LLM judge unavailable (no GOOGLE_API_KEY)")

    from google import genai

    model_id = model or os.getenv("GEMINI_JUDGE_MODEL", os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash"))
    client = genai.Client(api_key=api_key)
    context_text = "\n\n".join(
        f"[{i}] {p.strip()[:1200]}" for i, p in enumerate(context_passages[:6], start=1)
    ) or "(no context retrieved)"
    prompt = _JUDGE_PROMPT.format(
        question=question.strip(),
        expected=expected_answer.strip()[:2000],
        context=context_text,
        actual=actual_answer.strip()[:2000],
    )

    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        text = (response.text or "").strip()
    except Exception:
        logger.exception("judge_call_failed")
        return JudgeScore(0.0, 0.0, 0.0, 0.0, 0.0, "Judge LLM call failed")

    payload = _parse_json_payload(text)
    if not isinstance(payload, dict):
        logger.warning("judge_parse_failed raw=%r", text[:200])
        return JudgeScore(0.0, 0.0, 0.0, 0.0, 0.0, f"Unparseable judge output: {text[:160]}")

    faith = _clamp(payload.get("faithfulness", 0))
    rel = _clamp(payload.get("answer_relevance", 0))
    ctx = _clamp(payload.get("context_recall", 0))
    corr = _clamp(payload.get("correctness", 0))
    overall_raw = payload.get("overall")
    if overall_raw is None:
        overall = round(0.30 * corr + 0.30 * faith + 0.20 * rel + 0.20 * ctx)
    else:
        overall = _clamp(overall_raw)
    return JudgeScore(
        faithfulness=faith,
        answer_relevance=rel,
        context_recall=ctx,
        correctness=corr,
        overall=overall,
        rationale=str(payload.get("rationale", "")).strip()[:400],
    )
