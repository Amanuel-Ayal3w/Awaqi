"""
Heuristics for detecting corrupt PDF text layers and poor OCR output.

MoR PDFs often ship with a broken embedded text layer (custom fonts / bad ToUnicode).
PyMuPDF returns long gibberish strings, which bypasses Tesseract and can still pass
naive OCR confidence checks when ``amh`` traineddata is missing.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


# Unicode blocks for Ethiopic script (Amharic)
def _is_ethiopic(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    return (0x1200 <= o <= 0x137F) or (0x1380 <= o <= 0x139F) or (0x2D80 <= o <= 0x2DDF)


@dataclass(frozen=True)
class TextQualityAssessment:
    is_likely_corrupt: bool
    ethiopic_ratio: float
    letter_ratio: float
    symbol_ratio: float
    reasons: tuple[str, ...]


def _meaningful_chars(text: str) -> str:
    return "".join(c for c in text if not c.isspace())


def assess_extracted_text(text: str, *, min_chars: int = 80) -> TextQualityAssessment:
    """
    Score extracted page/document text. Corrupt PDF layers and eng-only OCR on
    Amharic scans both tend to have very low Ethiopic ratio and high symbol noise.
    """
    sample = (text or "").strip()
    chars = _meaningful_chars(sample)
    n = len(chars)
    reasons: list[str] = []

    if n < min_chars:
        return TextQualityAssessment(
            is_likely_corrupt=False,
            ethiopic_ratio=0.0,
            letter_ratio=0.0,
            symbol_ratio=0.0,
            reasons=(),
        )

    ethiopic = sum(1 for c in chars if _is_ethiopic(c))
    latin = sum(1 for c in chars if c.isascii() and c.isalpha())
    digits = sum(1 for c in chars if c.isdigit())
    symbols = sum(1 for c in chars if c in '#$%&*<>@^`~|\\{}[]')
    other_letters = sum(
        1 for c in chars if c.isalpha() and not _is_ethiopic(c) and not c.isascii()
    )
    letters = ethiopic + latin + other_letters

    ethiopic_ratio = ethiopic / n
    letter_ratio = letters / n
    symbol_ratio = symbols / n
    digit_ratio = digits / n

    # Broken embedded layers often repeat proclamation fragments as Latin junk.
    if len(re.findall(r"\b\d{1,4}/\d{2,4}\b", sample)) >= 3 and ethiopic_ratio < 0.03:
        reasons.append("repeated_proclamation_tokens_without_ethiopic")

    if letter_ratio < 0.22:
        reasons.append("low_letter_ratio")

    if symbol_ratio > 0.06 and ethiopic_ratio < 0.04:
        reasons.append("high_symbol_noise")

    if digit_ratio > 0.35 and ethiopic_ratio < 0.05:
        reasons.append("digit_heavy_non_ethiopic")

    # Very long runs without any Ethiopic on what is likely an Amharic directive.
    if n >= 200 and ethiopic == 0 and letter_ratio < 0.5:
        reasons.append("no_ethiopic_in_long_extract")

    is_corrupt = len(reasons) >= 2 or (
        len(reasons) == 1 and reasons[0] in ("no_ethiopic_in_long_extract", "low_letter_ratio")
    )

    return TextQualityAssessment(
        is_likely_corrupt=is_corrupt,
        ethiopic_ratio=round(ethiopic_ratio, 4),
        letter_ratio=round(letter_ratio, 4),
        symbol_ratio=round(symbol_ratio, 4),
        reasons=tuple(reasons),
    )


def is_corrupt_extracted_text(text: str) -> bool:
    return assess_extracted_text(text).is_likely_corrupt
