"""Lightweight heuristics for citation metadata (AWA-13)."""

from __future__ import annotations

import re


def guess_proclamation_number(title: str) -> str | None:
    """Match patterns like 285/2002 or 410/2017 in a document title."""
    if not title:
        return None
    m = re.search(r"\b(\d{1,4}/\d{2,4})\b", title)
    return m.group(1) if m else None


def guess_article_number_from_text(snippet: str) -> str | None:
    """Best-effort article number from chunk start (English / Amharic labels)."""
    if not snippet:
        return None
    head = snippet[:1200]
    m = re.search(
        r"(?:Article|Articles|አንቀጽ)\s*([0-9]+(?:\.[0-9]+)?)",
        head,
        re.IGNORECASE,
    )
    return m.group(1) if m else None
