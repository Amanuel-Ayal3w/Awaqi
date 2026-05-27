"""Tests for Gemini embedding helpers (no API calls)."""

import math

from ai_engine.gemini_embedder import _normalize


def test_normalize_unit_length():
    vec = _normalize([3.0, 4.0])
    assert len(vec) == 2
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6
