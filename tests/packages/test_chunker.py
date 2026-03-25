"""Tests for the ai-engine text chunker."""

from ai_engine.chunker import _pages_for_range, chunk_pages
from ai_engine.extractor import PageText


class TestChunkPages:
    def test_empty_pages(self):
        assert chunk_pages([]) == []

    def test_single_short_page(self):
        pages = [PageText(page_number=1, text="Hello world")]
        chunks = chunk_pages(pages)
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert "Hello world" in chunks[0].content
        assert chunks[0].metadata["pages"] == [1]

    def test_blank_pages_skipped(self):
        pages = [
            PageText(page_number=1, text=""),
            PageText(page_number=2, text="   "),
            PageText(page_number=3, text="Actual content"),
        ]
        chunks = chunk_pages(pages)
        assert len(chunks) >= 1
        assert all(3 in c.metadata["pages"] for c in chunks)

    def test_multiple_pages_chunked(self):
        text = "A" * 3000
        pages = [
            PageText(page_number=1, text=text),
            PageText(page_number=2, text=text),
        ]
        chunks = chunk_pages(pages, chunk_size=4000, overlap=400)
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_overlap_creates_shared_content(self):
        text = "word " * 1000  # 5000 chars
        pages = [PageText(page_number=1, text=text)]
        chunks = chunk_pages(pages, chunk_size=2000, overlap=500)
        assert len(chunks) >= 2
        # Overlapping content should exist between consecutive chunks
        first_end = chunks[0].content[-200:]
        second_start = chunks[1].content[:200]
        assert first_end in chunks[1].content or second_start in chunks[0].content

    def test_chunk_metadata_has_required_keys(self):
        pages = [PageText(page_number=1, text="Test content here")]
        chunks = chunk_pages(pages)
        for chunk in chunks:
            assert "pages" in chunk.metadata
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata

    def test_custom_chunk_size(self):
        text = "X" * 10000
        pages = [PageText(page_number=1, text=text)]
        small_chunks = chunk_pages(pages, chunk_size=500, overlap=50)
        large_chunks = chunk_pages(pages, chunk_size=5000, overlap=50)
        assert len(small_chunks) > len(large_chunks)

    def test_sequential_indices(self):
        pages = [PageText(page_number=1, text="Y" * 10000)]
        chunks = chunk_pages(pages, chunk_size=1000, overlap=100)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i


class TestPagesForRange:
    def test_single_page(self):
        boundaries = [(0, 1)]
        assert _pages_for_range(boundaries, 0, 100) == {1}

    def test_spans_two_pages(self):
        boundaries = [(0, 1), (500, 2)]
        assert _pages_for_range(boundaries, 400, 600) == {1, 2}

    def test_within_second_page(self):
        boundaries = [(0, 1), (500, 2), (1000, 3)]
        assert _pages_for_range(boundaries, 600, 800) == {2}

    def test_empty_boundaries(self):
        assert _pages_for_range([], 0, 100) == set()

    def test_range_covers_all_pages(self):
        boundaries = [(0, 1), (100, 2), (200, 3)]
        assert _pages_for_range(boundaries, 0, 300) == {1, 2, 3}
