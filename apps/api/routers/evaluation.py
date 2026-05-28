"""
Admin evaluation endpoints — serves RAG benchmark results computed offline by
``scripts/run_evaluation.py`` (results land as JSON under
``data/evaluations/runs/``).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.deps import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_data_dir() -> Path:
    """Allow override via EVAL_DATA_DIR; default to <repo>/data/evaluations."""
    override = os.getenv("EVAL_DATA_DIR")
    if override:
        return Path(override)
    # apps/api/routers/evaluation.py -> repo root is 3 parents up
    return Path(__file__).resolve().parents[3] / "data" / "evaluations"


def _runs_dir() -> Path:
    return _resolve_data_dir() / "runs"


def _benchmark_path() -> Path:
    return _resolve_data_dir() / "benchmark.json"


def _safe_run_file(run_id: str) -> Path:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="invalid run_id")
    path = (_runs_dir() / f"{run_id}.json").resolve()
    try:
        path.relative_to(_runs_dir().resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid run_id")
    return path


@router.get("/admin/evaluation/benchmark")
async def get_benchmark(_admin=Depends(get_current_admin)) -> dict[str, Any]:
    path = _benchmark_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="benchmark.json not found")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/admin/evaluation/runs")
async def list_runs(_admin=Depends(get_current_admin)) -> dict[str, Any]:
    runs_dir = _runs_dir()
    if not runs_dir.exists():
        return {"runs": []}
    entries: list[dict[str, Any]] = []
    for path in sorted(runs_dir.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as fh:
                doc = json.load(fh)
            summary = doc.get("summary") or {}
            entries.append({
                "run_id": summary.get("run_id") or path.stem,
                "mode": summary.get("mode"),
                "assistant_mode": summary.get("assistant_mode") or "basic",
                "k": summary.get("k"),
                "started_at": summary.get("started_at"),
                "finished_at": summary.get("finished_at"),
                "total_questions": summary.get("total_questions"),
                "avg_judge_overall": summary.get("avg_judge_overall"),
                "avg_hit_at_k": summary.get("avg_hit_at_k"),
                "avg_precision_at_k": summary.get("avg_precision_at_k"),
                "avg_recall_at_k": summary.get("avg_recall_at_k"),
                "avg_mrr": summary.get("avg_mrr"),
                "avg_ndcg_at_k": summary.get("avg_ndcg_at_k"),
                "avg_semantic_similarity": summary.get("avg_semantic_similarity"),
                "avg_latency_ms": summary.get("avg_latency_ms"),
                "avg_agent_tool_calls": summary.get("avg_agent_tool_calls"),
                "pct_agent_used_web_search": summary.get("pct_agent_used_web_search"),
                "benchmark": doc.get("benchmark"),
            })
        except Exception:
            logger.exception("eval_run_index_failed file=%s", path.name)
            continue
    return {"runs": entries}


@router.get("/admin/evaluation/runs/{run_id}")
async def get_run(
    run_id: str,
    _admin=Depends(get_current_admin),
) -> dict[str, Any]:
    path = _safe_run_file(run_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
