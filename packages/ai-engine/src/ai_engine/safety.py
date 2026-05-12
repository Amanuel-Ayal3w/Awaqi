"""
Query safety gate (AWA-28 — lightweight refusal without a separate classifier).

Blocks obvious profanity and empty / nonsense input. Encourages tax-related follow-up.
"""

from __future__ import annotations

import re

# Minimal English blocklist; extend cautiously (avoid blocking legitimate tax Latin).
_PROFANE = frozenset(
    {
        "fuck",
        "shit",
        "bitch",
        "asshole",
        "cunt",
        "nigger",
        "nigga",
        "faggot",
        "retard",
    }
)


def should_refuse_query(text: str) -> tuple[bool, str | None]:
    """
    Return ``(True, refusal_message)`` when the query must not be processed.

    Does not log the raw query body (AWA-64-friendly).
    """
    t = (text or "").strip()
    if not t:
        return True, "Please enter a tax-related question so I can help."

    lowered = re.sub(r"[^a-z0-9\s]", " ", t.lower())
    tokens = set(lowered.split())
    if tokens & _PROFANE:
        return (
            True,
            "I can’t help with that kind of language. Please ask a respectful tax or revenue question.",
        )

    # Very short non-alphanumeric spam
    alnum = re.sub(r"[^A-Za-z0-9\u1200-\u137F]", "", t)
    if len(alnum) < 2 and len(t) < 8:
        return True, "I didn’t catch a clear question. Try asking about VAT, income tax, or a specific regulation."

    return False, None
