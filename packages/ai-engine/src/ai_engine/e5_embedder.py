"""
multilingual-e5-large embeddings (AWA-14).

Uses ``passage:`` prefix for document chunks and ``query:`` for search queries (AWA-19).
"""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model: torch.nn.Module | None = None
_tokenizer: PreTrainedTokenizerBase | None = None

MODEL_NAME = os.getenv("E5_MODEL_NAME", "intfloat/multilingual-e5-large")
BATCH_SIZE = int(os.getenv("E5_EMBED_BATCH", "8"))


def _load_model() -> tuple[PreTrainedTokenizerBase, torch.nn.Module]:
    global _model, _tokenizer
    with _lock:
        if _model is None:
            from transformers import AutoModel, AutoTokenizer

            logger.info("Loading E5 model %s", MODEL_NAME)
            tok = AutoTokenizer.from_pretrained(MODEL_NAME)
            mdl = AutoModel.from_pretrained(MODEL_NAME)
            mdl.eval()
            _tokenizer = tok
            _model = mdl
        assert _tokenizer is not None and _model is not None
        return _tokenizer, _model


def get_tokenizer() -> PreTrainedTokenizerBase:
    tok, _ = _load_model()
    return tok


def _average_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_states.size()).float()
    summed = torch.sum(last_hidden_states * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


def _embed_prefixed_batch(texts: list[str], prefix: str) -> list[list[float]]:
    tokenizer, model = _load_model()
    prefixed = [f"{prefix}{t}" for t in texts]
    all_vecs: list[list[float]] = []

    with torch.inference_mode():
        for start in range(0, len(prefixed), BATCH_SIZE):
            batch = prefixed[start : start + BATCH_SIZE]
            enc = tokenizer(
                batch,
                max_length=min(512, tokenizer.model_max_length),
                padding=True,
                truncation=True,
                return_tensors="pt",
                verbose=False,
            )
            outputs = model(**enc)
            emb = _average_pool(outputs.last_hidden_state, enc["attention_mask"])
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
            all_vecs.extend(emb.cpu().tolist())
    return all_vecs


def embed_passages_sync(texts: list[str]) -> list[list[float]]:
    """Sync embedding for indexing (``passage:`` prefix)."""
    if not texts:
        return []
    return _embed_prefixed_batch(texts, "passage: ")


def embed_query_sync(text: str) -> list[float]:
    """Single query vector (``query:`` prefix)."""
    vecs = _embed_prefixed_batch([text], "query: ")
    return vecs[0] if vecs else []
