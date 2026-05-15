"""
Format Awaqi API responses into Telegram-compatible MarkdownV2.

Telegram's MarkdownV2 requires escaping several characters.
We keep formatting simple so it renders cleanly on all clients.
"""

import re
from typing import Optional

from .api_client import ChatResult, Citation

# Characters that must be escaped in MarkdownV2 outside of code/pre blocks
_ESCAPE_CHARS = r"\_*[]()~`>#+-=|{}.!"
_ESCAPE_RE = re.compile(r"([" + re.escape(_ESCAPE_CHARS) + r"])")


def _esc(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return _ESCAPE_RE.sub(r"\\\1", text)


def format_response(result: ChatResult, language: str = "en") -> str:
    """
    Build the full Telegram message text from a ChatResult.
    Includes the answer and a formatted citations block if present.
    """
    parts: list[str] = []

    # Main answer — escape so MarkdownV2 renders correctly
    parts.append(_esc(result.response_text))

    # Citations block
    if result.citations:
        parts.append("")  # blank line
        if language == "am":
            parts.append(_esc("--- ምንጮች ---"))
        else:
            parts.append(_esc("--- Sources ---"))

        for i, cite in enumerate(result.citations, 1):
            parts.append(_format_citation(i, cite))

    # Low-confidence disclaimer
    if 0.0 < result.confidence_score < 0.7:
        parts.append("")
        if language == "am":
            disclaimer = "ማስጠንቀቂያ: ይህ መረጃ ሙሉ ላይሆን ይችላል። እባክዎ ከኢ.ቫ.ባ. ባለስልጣን ጋር ያረጋግጡ።"
        else:
            disclaimer = "Note: This information may be incomplete. Please verify with an ERA officer."
        parts.append(_esc(f"⚠ {disclaimer}"))

    return "\n".join(parts)


def _format_citation(index: int, cite: Citation) -> str:
    """Format a single citation as a compact numbered line."""
    parts: list[str] = [f"\\[{index}\\]"]

    if cite.document_title:
        parts.append(_esc(cite.document_title))
    if cite.proclamation_number:
        parts.append(_esc(f"Proc. {cite.proclamation_number}"))
    if cite.article_number:
        parts.append(_esc(f"Art. {cite.article_number}"))
    if cite.page and cite.page > 0:
        parts.append(_esc(f"p.{cite.page}"))

    return " · ".join(parts)


def format_rate_limit_error(retry_seconds: int, language: str = "en") -> str:
    if language == "am":
        msg = f"ብዙ ጥያቄዎች። {retry_seconds} ሰከንድ ጠብቀው እንደገና ይሞክሩ።"
    else:
        msg = f"Too many requests. Please wait {retry_seconds} seconds and try again."
    return _esc(msg)


def format_error(language: str = "en") -> str:
    if language == "am":
        msg = "አሁን የታክስ ሕጎቹን መፈለግ አልቻልኩም። ትንሽ ቆይተው እንደገና ይሞክሩ።"
    else:
        msg = "I am unable to search the tax laws right now. Please try again in a moment."
    return _esc(msg)


_TELEGRAM_MAX_LEN = 4096


def split_message(text: str, max_len: int = _TELEGRAM_MAX_LEN) -> list[str]:
    """
    Split a long message into chunks that fit Telegram's 4096-character limit.

    Splits on newlines whenever possible so MarkdownV2 blocks are not broken
    mid-line.  Falls back to hard character splits only when a single line
    exceeds max_len.
    """
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in text.split("\n"):
        line_len = len(line) + 1  # +1 for the newline we'll re-add

        if current_len + line_len > max_len:
            if current_lines:
                chunks.append("\n".join(current_lines))
                current_lines = []
                current_len = 0

            # If a single line is longer than the limit, hard-split it
            while len(line) > max_len:
                chunks.append(line[:max_len])
                line = line[max_len:]
            if line:
                current_lines.append(line)
                current_len = len(line) + 1
        else:
            current_lines.append(line)
            current_len += line_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks
