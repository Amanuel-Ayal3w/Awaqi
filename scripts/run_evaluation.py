"""
Run the RAG evaluation benchmark.

Usage:
    uv run --package api python scripts/run_evaluation.py \
        --mode optimized \
        --k 10

    # Compare all three modes back-to-back:
    uv run --package api python scripts/run_evaluation.py --mode all

Outputs JSON run files under data/evaluations/runs/ that the admin UI
serves at /admin/evaluation.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from database import AsyncSessionLocal

from ai_engine.evaluation.dataset import load_benchmark
from ai_engine.evaluation.runner import run_evaluation, save_run

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s | %(message)s"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = REPO_ROOT / "data" / "evaluations" / "benchmark.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "evaluations" / "runs"


async def _run_one(mode: str, assistant_mode: str, k: int, benchmark_path: Path,
                   output_dir: Path, use_judge: bool, use_semantic_sim: bool) -> None:
    import json
    with benchmark_path.open("r", encoding="utf-8") as fh:
        bench_doc = json.load(fh)
    bench_name = bench_doc.get("name", benchmark_path.stem)
    items = load_benchmark(benchmark_path)
    print(f"[eval] loaded {len(items)} benchmark items from {benchmark_path}")
    print(
        f"[eval] retrieval_mode={mode} assistant_mode={assistant_mode} k={k} "
        f"judge={use_judge} semantic_sim={use_semantic_sim}"
    )
    async with AsyncSessionLocal() as db:
        summary, results = await run_evaluation(
            db, items,
            mode=mode,  # type: ignore[arg-type]
            assistant_mode=assistant_mode,  # type: ignore[arg-type]
            k=k,
            use_judge=use_judge,
            use_semantic_sim=use_semantic_sim,
        )
    file_path = save_run(output_dir, summary, results, benchmark_name=bench_name)
    print(f"[eval] saved {file_path}")
    print(
        f"[eval] summary mode={summary.mode} asst={summary.assistant_mode} "
        f"questions={summary.total_questions}"
    )
    print(
        f"        Retrieval — Hit@{k}={summary.avg_hit_at_k:.3f}  "
        f"P@{k}={summary.avg_precision_at_k:.3f}  "
        f"R@{k}={summary.avg_recall_at_k:.3f}  "
        f"MRR={summary.avg_mrr:.3f}  "
        f"NDCG@{k}={summary.avg_ndcg_at_k:.3f}"
    )
    print(
        f"        Generation — Judge overall={summary.avg_judge_overall:.2f}/10  "
        f"Faith={summary.avg_judge_faithfulness:.2f}  "
        f"Rel={summary.avg_judge_answer_relevance:.2f}  "
        f"CtxRecall={summary.avg_judge_context_recall:.2f}  "
        f"Correct={summary.avg_judge_correctness:.2f}  "
        f"SemSim={summary.avg_semantic_similarity:.3f}"
    )
    if assistant_mode == "awaqi_max":
        print(
            f"        Agent — avg tool calls={summary.avg_agent_tool_calls:.2f}  "
            f"web search used in {summary.pct_agent_used_web_search * 100:.0f}% of questions"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the RAG evaluation benchmark")
    parser.add_argument(
        "--mode",
        choices=["optimized", "dense_only", "bm25_only", "all"],
        default="optimized",
        help="Retrieval strategy used under the hood (hybrid/dense-only/bm25-only).",
    )
    parser.add_argument(
        "--assistant",
        choices=["basic", "awaqi_max", "both"],
        default="basic",
        help="Answer pipeline: `basic` single-shot RAG vs `awaqi_max` ReAct agent.",
    )
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-judge", action="store_true",
        help="Skip the LLM-as-judge step (faster, free).",
    )
    parser.add_argument(
        "--no-semantic-sim", action="store_true",
        help="Skip embedding-based semantic similarity.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format=LOG_FORMAT,
    )

    if not args.benchmark.exists():
        print(f"[eval] benchmark not found at {args.benchmark}", file=sys.stderr)
        return 2

    modes = ["optimized", "dense_only", "bm25_only"] if args.mode == "all" else [args.mode]
    assistants = ["basic", "awaqi_max"] if args.assistant == "both" else [args.assistant]
    for assistant in assistants:
        for mode in modes:
            asyncio.run(
                _run_one(
                    mode=mode,
                    assistant_mode=assistant,
                    k=args.k,
                    benchmark_path=args.benchmark,
                    output_dir=args.output_dir,
                    use_judge=not args.no_judge,
                    use_semantic_sim=not args.no_semantic_sim,
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
