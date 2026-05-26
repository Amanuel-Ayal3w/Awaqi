"""Tests for corrupt PDF text / OCR quality heuristics."""

from ai_engine.text_quality import assess_extracted_text, is_corrupt_extracted_text

GIBBERISH_SAMPLE = """
1 71/ 71/ 71/ 71/200 200 200 2004 " #"$ % &'#&() % *+ (,-./" 012 3 45"
67 89 7 :" (&; <=8( *>? % @AB CD./" E'F'E+7G HIJ / 0127 K7/" <*89 01+' 6D./"
""".strip()

AMHARIC_SAMPLE = """
የገቢዎች ሚኒስቴር የአሰራር ስርዓት መመሪያ ቁጥር 71/2004
አንቀጽ 3. የተፈጻሚነት ወሰን
""".strip()


def test_detects_corrupt_pdf_layer_gibberish():
    assert is_corrupt_extracted_text(GIBBERISH_SAMPLE)


def test_accepts_reasonable_amharic_text():
    assert not is_corrupt_extracted_text(AMHARIC_SAMPLE)


def test_short_text_not_flagged():
    assert not is_corrupt_extracted_text("short")


def test_assessment_includes_reasons_for_gibberish():
    a = assess_extracted_text(GIBBERISH_SAMPLE)
    assert a.is_likely_corrupt
    assert a.ethiopic_ratio < 0.02
    assert len(a.reasons) >= 1
