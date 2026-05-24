"""Unit tests for sparse retrieval helpers (FTS + BM25 ranking)."""

from __future__ import annotations

import uuid

import pytest
from database.fts import _bm25_scores, _tokenize, bm25_search_chunk_ids


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def execute(self, stmt, params):
        self.calls.append((str(stmt), params))
        return _FakeResult(self._responses.pop(0))


class TestTokenize:
    def test_tokenize_casefolds_and_keeps_unicode_words(self):
        tokens = _tokenize("VAT Registration የቫት 285/2002")
        assert "vat" in tokens
        assert "registration" in tokens
        assert "የቫት" in tokens
        assert "285" in tokens
        assert "2002" in tokens


class TestBM25Scores:
    def test_scores_rank_relevant_document_higher(self):
        query_tokens = _tokenize("vat registration threshold")
        docs = [
            _tokenize("VAT registration threshold is one million birr"),
            _tokenize("income tax withholding"),
        ]
        scores = _bm25_scores(query_tokens, docs)
        assert scores[0] > scores[1]


class TestBM25SearchChunkIds:
    @pytest.mark.asyncio
    async def test_returns_ranked_ids_from_fts_candidates(self):
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        id3 = uuid.uuid4()
        rows = [
            (id1, "income tax withholding rules"),
            (id2, "vat registration threshold vat registration"),
            (id3, "excise tax schedules"),
        ]
        db = _FakeSession([rows])

        ranked = await bm25_search_chunk_ids(db, "vat registration threshold", limit=2)

        assert ranked == [id2, id1]
        assert len(db.calls) == 1

    @pytest.mark.asyncio
    async def test_falls_back_to_trigram_when_fts_empty(self):
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        fts_rows = []
        trgm_rows = [
            (id1, "vat registration threshold is one million birr"),
            (id2, "income tax monthly declaration"),
        ]
        db = _FakeSession([fts_rows, trgm_rows])

        ranked = await bm25_search_chunk_ids(db, "vat registration threshold", limit=2)

        assert ranked == [id1, id2]
        assert len(db.calls) == 2

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_without_db_call(self):
        db = _FakeSession([])
        ranked = await bm25_search_chunk_ids(db, "   ")
        assert ranked == []
        assert db.calls == []
