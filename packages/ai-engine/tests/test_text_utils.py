"""Unicode normalization (AWA-10)."""

from ai_engine.text_utils import normalize_unicode_nfc


def test_nfc_amharic_stable() -> None:
    s = "\u1200\u1201"  # Ethiopic syllables
    assert normalize_unicode_nfc(s) == s
