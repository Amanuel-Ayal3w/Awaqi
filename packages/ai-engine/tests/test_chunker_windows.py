"""Pure unit tests for token window overlap (no model download)."""

from ai_engine.chunker_tokens import iter_token_windows


def test_iter_token_windows_overlap() -> None:
    ids = list(range(500))
    max_t = 100
    min_o = 50
    windows = iter_token_windows(ids, max_chunk_tokens=max_t, min_overlap_tokens=min_o)
    assert len(windows) >= 2
    for i in range(len(windows) - 1):
        a0, a1 = windows[i]
        b0, b1 = windows[i + 1]
        shared = min(a1, b1) - max(a0, b0)
        assert shared >= min_o
