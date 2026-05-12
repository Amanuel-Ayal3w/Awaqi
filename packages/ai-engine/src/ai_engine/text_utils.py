"""Unicode and text normalization for ingestion (AWA-10 / AWA-74)."""

from __future__ import annotations

import unicodedata


def normalize_unicode_nfc(text: str) -> str:
    """Normalize to NFC so Ethiopic and composed characters round-trip consistently."""
    return unicodedata.normalize("NFC", text or "")
