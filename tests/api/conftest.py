"""
API-test fixtures that intercept heavy AI calls so integration tests stay
fast and never depend on real ML models or external APIs.

embed_passages_sync is patched for every test in this directory: upload and
ingest-text endpoints call it internally, and it returns E5 (1024-d) vectors
while the DB column expects 1536-d (Gemini).  Replacing it with a no-op that
yields 1536-d zero vectors fixes the dimension mismatch without changing any
production code.

Mark a test with @pytest.mark.real_embedder to skip the patch.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

EMBEDDING_DIM = 1536


@pytest.fixture(autouse=True)
def _mock_embed_passages(request):
    if request.node.get_closest_marker("real_embedder"):
        yield
        return

    def _fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    with patch("ai_engine.ingest.embed_passages_sync", side_effect=_fake_embed):
        yield
