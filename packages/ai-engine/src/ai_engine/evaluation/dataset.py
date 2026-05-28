"""Benchmark dataset loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GroundTruth:
    proclamation_number: str | None
    article_numbers: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class BenchmarkItem:
    id: str
    question: str
    expected_answer: str
    language: str
    topic: str
    ground_truth: GroundTruth


def load_benchmark(path: str | Path) -> list[BenchmarkItem]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = json.load(fh)
    items: list[BenchmarkItem] = []
    for entry in raw.get("items", []):
        gt = entry.get("ground_truth") or {}
        items.append(
            BenchmarkItem(
                id=entry["id"],
                question=entry["question"],
                expected_answer=entry["expected_answer"],
                language=entry.get("language", "am"),
                topic=entry.get("topic", "general"),
                ground_truth=GroundTruth(
                    proclamation_number=gt.get("proclamation_number"),
                    article_numbers=list(gt.get("article_numbers", []) or []),
                    keywords=list(gt.get("keywords", []) or []),
                ),
            )
        )
    return items
