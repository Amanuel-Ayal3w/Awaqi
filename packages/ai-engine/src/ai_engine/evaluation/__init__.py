"""
RAG evaluation module.

Implements the standard RAG evaluation metric stack:

Retrieval
  - Hit@k        — did any relevant document appear in the top-k?
  - Precision@k  — fraction of top-k that are relevant
  - Recall@k     — fraction of all relevant docs retrieved in top-k
  - MRR          — mean reciprocal rank of the first relevant doc
  - NDCG@k       — position-discounted relevance

Generation
  - LLM-as-judge — Gemini scores 1..10 across Faithfulness, Answer Relevance,
                   Context Recall, Correctness, plus an aggregate Overall 1..10
  - Semantic similarity — cosine of embed(expected) vs embed(actual)

A ground-truth item is "relevant" if its document's ``proclamation_number``
matches the benchmark item's ``ground_truth.proclamation_number``.
"""

from ai_engine.evaluation.dataset import BenchmarkItem, load_benchmark
from ai_engine.evaluation.judge import JudgeScore, judge_answer
from ai_engine.evaluation.metrics import (
    cosine_similarity,
    hit_at_k,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

__all__ = [
    "BenchmarkItem",
    "load_benchmark",
    "JudgeScore",
    "judge_answer",
    "cosine_similarity",
    "hit_at_k",
    "mrr",
    "ndcg_at_k",
    "precision_at_k",
    "recall_at_k",
]
