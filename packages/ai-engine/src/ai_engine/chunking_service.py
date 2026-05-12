"""
SDS-aligned chunking façade (Phase A1).

Token-window chunking for multilingual-e5 (see ``chunker_tokens``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_engine.chunker import Chunk
from ai_engine.chunker_tokens import chunk_pages_tokenized as _chunk_pages_tokenized

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

    from ai_engine.extractor import PageText


class ChunkingService:
    """Token-based sliding windows with overlap (AWA-12)."""

    @staticmethod
    def chunk_pages_tokenized(
        pages: list["PageText"],
        tokenizer: "PreTrainedTokenizerBase",
        *,
        max_chunk_tokens: int | None = None,
        min_overlap_tokens: int | None = None,
    ) -> list[Chunk]:
        kwargs: dict[str, int] = {}
        if max_chunk_tokens is not None:
            kwargs["max_chunk_tokens"] = max_chunk_tokens
        if min_overlap_tokens is not None:
            kwargs["min_overlap_tokens"] = min_overlap_tokens
        return _chunk_pages_tokenized(pages, tokenizer, **kwargs)
