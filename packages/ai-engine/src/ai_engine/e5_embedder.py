"""
multilingual-e5-large tokenizer utilities (chunking only).

RAG embeddings use Gemini (see ``embeddings.py``). This module is intentionally
limited to tokenizer loading for token-window chunking compatibility.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_tokenizer: PreTrainedTokenizerBase | None = None

MODEL_NAME = os.getenv("E5_MODEL_NAME", "intfloat/multilingual-e5-large")


def _load_tokenizer() -> PreTrainedTokenizerBase:
    global _tokenizer
    with _lock:
        if _tokenizer is None:
            from transformers import AutoTokenizer

            logger.info("Loading E5 tokenizer %s", MODEL_NAME)
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        assert _tokenizer is not None
        return _tokenizer


def get_tokenizer() -> PreTrainedTokenizerBase:
    return _load_tokenizer()
