"""Lightweight heuristics for citation metadata (AWA-13)."""

from __future__ import annotations

import re


def guess_proclamation_number(title: str) -> str | None:
    """Match patterns like 285/2002, 410-2017, or 410_2009 in a document title.

    Real-world titles in the corpus mix separators:
      "Federal Income Tax Regulation No 410-2017.pdf"   →  "410/2017"
      "ደንብ-ቁጥር-410-2009.pdf"                              →  "410/2009"
      "Proclamation 1395/2017 Income Tax Amendment.pdf"  →  "1395/2017"

    Output is normalised to the canonical ``NUMBER/YEAR`` form so the runner's
    loose-match logic can compare across documents that disagree on separator.
    """
    if not title:
        return None
    m = re.search(r"\b(\d{1,4})\s*[/_\-]\s*(\d{2,4})\b", title)
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}"


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
