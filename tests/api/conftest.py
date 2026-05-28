"""
API-test fixtures that intercept heavy AI calls so integration tests stay
fast and never depend on real ML models or external APIs.

embed_passages_sync is patched for every test in this directory: upload and
ingest-text endpoints call it internally.  The DB now stores native Gemini
3072-d vectors, so tests use fixed-size 3072-d zero vectors to avoid depending
on external embedding APIs.

Mark a test with @pytest.mark.real_embedder to skip the patch.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

EMBEDDING_DIM = 3072


@pytest.fixture(autouse=True)
def _mock_embed_passages(request):
    if request.node.get_closest_marker("real_embedder"):
        yield
        return

    def _fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    with patch("ai_engine.ingest.embed_passages_sync", side_effect=_fake_embed):
        yield
