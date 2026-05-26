"""Unit tests for hybrid retrieval helpers (no DB or embedder calls)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_engine.hybrid_retrieval import load_chunks_by_ids, reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_empty_input_returns_empty(self):
        assert reciprocal_rank_fusion([]) == []

    def test_single_list_preserves_rank_order(self):
        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        result = reciprocal_rank_fusion([ids])
        assert result == ids

    def test_top_n_limits_output_length(self):
        ids = [uuid.uuid4() for _ in range(20)]
        result = reciprocal_rank_fusion([ids], top_n=5)
        assert len(result) == 5

    def test_agreement_across_lists_boosts_rank(self):
        id_a, id_b = uuid.uuid4(), uuid.uuid4()
        # id_a ranks first in both lists → higher fused score than id_b
        result = reciprocal_rank_fusion([[id_a, id_b], [id_a, id_b]])
        assert result[0] == id_a

    def test_no_duplicates_in_output(self):
        shared = uuid.uuid4()
        other = uuid.uuid4()
        result = reciprocal_rank_fusion([[shared], [shared, other]])
        assert result.count(shared) == 1

    def test_result_contains_all_unique_ids(self):
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        result = reciprocal_rank_fusion([[a, b], [b, c]])
        assert set(result) == {a, b, c}

    def test_single_id_single_list(self):
        only = uuid.uuid4()
        result = reciprocal_rank_fusion([[only]])
        assert result == [only]

    def test_k_parameter_shifts_scores_but_not_relative_order(self):
        ids = [uuid.uuid4(), uuid.uuid4()]
        r1 = reciprocal_rank_fusion([ids], k=10)
        r2 = reciprocal_rank_fusion([ids], k=100)
        assert r1 == r2

    def test_returns_list_type(self):
        result = reciprocal_rank_fusion([[uuid.uuid4()]])
        assert isinstance(result, list)


class TestLoadChunksByIds:
    async def test_empty_ids_returns_empty(self):
        db = MagicMock()
        result = await load_chunks_by_ids(db, [])
        assert result == []
        db.execute.assert_not_called()

    async def test_preserves_fused_order(self):
        id_a, id_b, id_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        chunk_a = MagicMock()
        chunk_a.id = id_a
        chunk_b = MagicMock()
        chunk_b.id = id_b
        chunk_c = MagicMock()
        chunk_c.id = id_c

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [chunk_b, chunk_c, chunk_a]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        result = await load_chunks_by_ids(db, [id_a, id_b, id_c])
        assert [c.id for c in result] == [id_a, id_b, id_c]

    async def test_missing_id_in_db_goes_to_end(self):
        id_known = uuid.uuid4()
        id_unknown = uuid.uuid4()

        chunk = MagicMock()
        chunk.id = id_known

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [chunk]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        result = await load_chunks_by_ids(db, [id_unknown, id_known])
        assert result[0].id == id_known
