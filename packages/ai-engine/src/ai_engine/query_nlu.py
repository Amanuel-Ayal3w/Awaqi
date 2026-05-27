"""
Lightweight query language handling (AWA-18-style, without bundling FastText).

Detects Amharic (Ethiopic script) vs Latin vs mixed for logging and downstream use.
"""

from __future__ import annotations

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

Ethiopic = re.compile(r"[\u1200-\u137F]")
LatinLetters = re.compile(r"[A-Za-z]")


def detect_query_language(text: str) -> Literal["am", "en", "mixed"]:
    """
    Heuristic: if both Ethiopic and Latin letters appear → ``mixed``;
    elif Ethiopic → ``am``; else ``en``.
    """
    t = text.strip()
    if not t:
        return "en"
    has_eth = bool(Ethiopic.search(t))
    has_lat = bool(LatinLetters.search(t))
    if has_eth and has_lat:
        return "mixed"
    if has_eth:
        return "am"
    return "en"


def build_retrieval_query_text(user_query: str, *, taxpayer_category: str | None) -> str:
    """
    Optional category bias prepended to the user query before Gemini embedding (AWA-19).
    """
    q = user_query.strip()
    if not q:
        return q
    cat = (taxpayer_category or "").strip()
    if not cat:
        return q
    return f"Taxpayer category: {cat}. Question: {q}"


def build_e5_query_text(user_query: str, *, taxpayer_category: str | None) -> str:
    """Deprecated alias — use ``build_retrieval_query_text``."""
    return build_retrieval_query_text(user_query, taxpayer_category=taxpayer_category)
