"""
Token-based chunking aligned to multilingual-e5 tokenizer (AWA-12).

Sliding window on tokenizer ids with overlap (default >= 50 tokens, ~10% of max).
``max_chunk_tokens`` defaults below the model's 512-token limit because chunks are
``decode(window_ids)`` then re-tokenized at embed time as ``passage: `` + text; that
round-trip can grow versus ``len(window_ids)`` (~10%+). Embedding uses truncation,
but staying under budget avoids noisy tokenizer warnings and information loss.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_engine.chunker import Chunk
from ai_engine.extractor import PageText

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

logger = logging.getLogger(__name__)

# Budget < 512: room for ``passage: `` prefix + decode→encode expansion vs raw ids.
DEFAULT_MAX_CHUNK_TOKENS = 448
DEFAULT_MIN_OVERLAP_TOKENS = 50


def _build_full_text(pages: list[PageText]) -> tuple[str, list[tuple[int, int]]]:
    """Concatenate page texts with markers; return (full_text, page_boundaries)."""
    full_text = ""
    boundaries: list[tuple[int, int]] = []
    for page in pages:
        if not page.text.strip():
            continue
        boundaries.append((len(full_text), page.page_number))
        full_text += page.text + "\n\n"
    return full_text, boundaries


def _pages_for_char_range(
    boundaries: list[tuple[int, int]],
    start: int,
    end: int,
) -> list[int]:
    pages: set[int] = set()
    for i, (offset, page_num) in enumerate(boundaries):
        next_offset = boundaries[i + 1][0] if i + 1 < len(boundaries) else 10**12
        if offset < end and next_offset > start:
            pages.add(page_num)
    return sorted(pages)


def iter_token_windows(
    ids: list[int],
    *,
    max_chunk_tokens: int,
    min_overlap_tokens: int,
) -> list[tuple[int, int]]:
    """Return list of (start, end) half-open spans over ``ids``."""
    if not ids:
        return []
    overlap = max(min_overlap_tokens, int(max_chunk_tokens * 0.1))
    overlap = min(overlap, max_chunk_tokens - 1)
    step = max(max_chunk_tokens - overlap, 1)

    windows: list[tuple[int, int]] = []
    start_idx = 0
    while start_idx < len(ids):
        end_idx = min(start_idx + max_chunk_tokens, len(ids))
        windows.append((start_idx, end_idx))
        if end_idx >= len(ids):
            break
        start_idx += step
    return windows


def chunk_pages_tokenized(
    pages: list[PageText],
    tokenizer: PreTrainedTokenizerBase,
    *,
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    min_overlap_tokens: int = DEFAULT_MIN_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Sliding-window chunking on tokenizer ids with overlap."""
    if not pages:
        return []

    full_text, boundaries = _build_full_text(pages)
    if not full_text.strip():
        return []

    # Full-document encode only builds windows over ids (never fed whole to E5).
    # ``verbose=False`` avoids transformers ``logger.warning`` on len(ids) > model_max_length.
    ids = tokenizer.encode(full_text, add_special_tokens=False, verbose=False)
    if not ids:
        return []

    overlap = max(min_overlap_tokens, int(max_chunk_tokens * 0.1))
    overlap = min(overlap, max_chunk_tokens - 1)
    windows = iter_token_windows(
        ids, max_chunk_tokens=max_chunk_tokens, min_overlap_tokens=min_overlap_tokens
    )

    ratio = len(full_text) / max(len(ids), 1)
    chunks: list[Chunk] = []
    for start_idx, end_idx in windows:
        window_ids = ids[start_idx:end_idx]
        text = tokenizer.decode(window_ids, skip_special_tokens=True).strip()
        if not text:
            text = "\n"
        char_start = max(int(start_idx * ratio) - 1, 0)
        char_end = min(len(full_text), int(end_idx * ratio) + 1)
        page_nums = _pages_for_char_range(boundaries, char_start, char_end)
        chunks.append(
            Chunk(
                index=len(chunks),
                content=text,
                metadata={
                    "token_start": start_idx,
                    "token_end": end_idx,
                    "pages": page_nums,
                    "max_chunk_tokens": max_chunk_tokens,
                    "overlap_tokens": overlap,
                },
            )
        )

    logger.info(
        "Token-chunked %d tokens into %d chunks (max=%d overlap>=%d)",
        len(ids),
        len(chunks),
        max_chunk_tokens,
        min_overlap_tokens,
    )
    return chunks


def verify_chunk_token_constraints(
    tokenizer: PreTrainedTokenizerBase,
    chunks: list[Chunk],
    ids: list[int],
    *,
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    min_overlap_tokens: int = DEFAULT_MIN_OVERLAP_TOKENS,
) -> None:
    """Raise AssertionError if sliding-window constraints are violated."""
    windows = iter_token_windows(
        ids, max_chunk_tokens=max_chunk_tokens, min_overlap_tokens=min_overlap_tokens
    )
    assert len(chunks) == len(windows), "chunk count mismatch"

    for i, c in enumerate(chunks):
        a0, a1 = windows[i]
        span_len = a1 - a0
        assert span_len <= max_chunk_tokens, (
            f"chunk {c.index} window span {span_len} tokens > {max_chunk_tokens}"
        )

    for i in range(len(windows) - 1):
        a0, a1 = windows[i]
        b0, b1 = windows[i + 1]
        shared_start = max(a0, b0)
        shared_end = min(a1, b1)
        shared_len = max(0, shared_end - shared_start)
        assert shared_len >= min_overlap_tokens, (
            f"windows {i},{i+1} share {shared_len} tokens < {min_overlap_tokens}"
        )
