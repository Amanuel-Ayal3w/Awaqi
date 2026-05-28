"""Unit tests for rag_answer helpers (no LLM calls)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from ai_engine.rag_answer import (
    _chunk_meta_page,
    _extractive_answer,
    answer_from_chunks,
    chunks_to_citations,
    estimate_confidence,
)


def _make_chunk(content: str, meta: dict | None = None) -> MagicMock:
    ch = MagicMock()
    ch.content = content
    ch.chunk_metadata = meta or {}
    return ch


class TestChunkMetaPage:
    def test_none_meta_returns_1(self):
        assert _chunk_meta_page(None) == 1

    def test_empty_meta_returns_1(self):
        assert _chunk_meta_page({}) == 1

    def test_pages_list_returns_first(self):
        assert _chunk_meta_page({"pages": [5, 6]}) == 5

    def test_empty_pages_list_returns_1(self):
        assert _chunk_meta_page({"pages": []}) == 1

    def test_non_int_page_returns_1(self):
        assert _chunk_meta_page({"pages": ["bad"]}) == 1


class TestChunksToCitations:
    def test_empty_chunks_returns_empty_list(self):
        assert chunks_to_citations([]) == []

    def test_uses_document_title_as_source(self):
        ch = _make_chunk("content", {"document_title": "Tax Law 2023", "pages": [3]})
        result = chunks_to_citations([ch])
        assert result[0]["source"] == "Tax Law 2023"
        assert result[0]["page"] == 3

    def test_falls_back_to_source_url(self):
        ch = _make_chunk("content", {"source_url": "http://mor.gov.et/doc.pdf"})
        result = chunks_to_citations([ch])
        assert result[0]["source"] == "http://mor.gov.et/doc.pdf"

    def test_falls_back_to_regulation_label(self):
        ch = _make_chunk("content", {})
        result = chunks_to_citations([ch])
        assert result[0]["source"] == "Regulation"

    def test_excerpt_is_trimmed_to_600_chars(self):
        ch = _make_chunk("x" * 800)
        result = chunks_to_citations([ch])
        assert len(result[0]["text"]) <= 600

    def test_empty_content_uses_placeholder(self):
        ch = _make_chunk("")
        result = chunks_to_citations([ch])
        assert result[0]["text"] == "(empty excerpt)"

    def test_caps_at_8_chunks(self):
        chunks = [_make_chunk(f"chunk {i}") for i in range(12)]
        result = chunks_to_citations(chunks)
        assert len(result) == 8

    def test_citation_has_required_keys(self):
        ch = _make_chunk("some text")
        result = chunks_to_citations([ch])
        for key in ("source", "page", "text", "document_title", "proclamation_number", "article_number"):
            assert key in result[0]

    def test_proclamation_number_propagated(self):
        ch = _make_chunk("text", {"proclamation_number": "285/2002"})
        result = chunks_to_citations([ch])
        assert result[0]["proclamation_number"] == "285/2002"

    def test_empty_proclamation_number_is_none(self):
        ch = _make_chunk("text", {"proclamation_number": ""})
        result = chunks_to_citations([ch])
        assert result[0]["proclamation_number"] is None


class TestEstimateConfidence:
    def test_no_chunks_returns_zero(self):
        assert estimate_confidence([]) == 0.0

    def test_one_chunk_returns_positive(self):
        score = estimate_confidence([MagicMock()])
        assert score > 0.0

    def test_five_chunks_is_capped_at_0_9(self):
        chunks = [MagicMock() for _ in range(5)]
        assert estimate_confidence(chunks) <= 0.9

    def test_many_chunks_capped_at_0_9(self):
        chunks = [MagicMock() for _ in range(20)]
        assert estimate_confidence(chunks) <= 0.9

    def test_more_chunks_higher_confidence(self):
        assert estimate_confidence([MagicMock()]) < estimate_confidence([MagicMock(), MagicMock()])


class TestExtractiveAnswer:
    def test_no_chunks_returns_fallback(self):
        result = _extractive_answer("VAT rate?", [])
        assert "knowledge base" in result.lower() or "not find" in result.lower()

    def test_includes_original_query(self):
        ch = _make_chunk("VAT is charged at 15%.")
        result = _extractive_answer("VAT rate?", [ch])
        assert "VAT rate?" in result

    def test_includes_chunk_excerpt(self):
        ch = _make_chunk("VAT is charged at 15%.")
        result = _extractive_answer("VAT rate?", [ch])
        assert "VAT" in result

    def test_caps_at_5_chunks(self):
        chunks = [_make_chunk(f"passage {i}") for i in range(10)]
        result = _extractive_answer("query", chunks)
        assert result.count("[") <= 5


class TestAnswerFromChunks:
    async def test_no_chunks_returns_fallback_text(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        text, cites, score, _follow_ups = await answer_from_chunks("q?", [], language="en")
        assert "knowledge base" in text.lower()
        assert cites == []
        assert score == 0.0

    async def test_with_chunks_uses_extractive_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        ch = _make_chunk("VAT is applied at 15%.", {"document_title": "VAT Proc"})
        text, cites, score, _follow_ups = await answer_from_chunks("VAT rate?", [ch], language="en")
        assert text
        assert len(cites) == 1
        assert score > 0.0

    async def test_returns_citations_for_each_chunk(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        chunks = [_make_chunk(f"passage {i}") for i in range(3)]
        _, cites, _, _follow_ups = await answer_from_chunks("question", chunks, language="en")
        assert len(cites) == 3

    async def test_confidence_positive_with_chunks(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        ch = _make_chunk("Tax info here.")
        _, _, score, _follow_ups = await answer_from_chunks("tax?", [ch], language="en")
        assert score > 0.0
