"""Unit tests for language detection and query building (ai_engine.query_nlu)."""

from ai_engine.query_nlu import build_e5_query_text, detect_query_language


class TestDetectQueryLanguage:
    def test_plain_english_is_en(self):
        assert detect_query_language("How do I file my income tax return?") == "en"

    def test_amharic_script_is_am(self):
        assert detect_query_language("ቀረጥ ምን ያህል ነው") == "am"

    def test_mixed_script_is_mixed(self):
        assert detect_query_language("What is ቀረጥ rate?") == "mixed"

    def test_empty_string_defaults_to_en(self):
        assert detect_query_language("") == "en"

    def test_whitespace_only_defaults_to_en(self):
        assert detect_query_language("   ") == "en"

    def test_digits_only_default_to_en(self):
        assert detect_query_language("12345") == "en"

    def test_single_amharic_char_is_am(self):
        assert detect_query_language("ሀ") == "am"

    def test_punctuation_only_is_en(self):
        assert detect_query_language("???") == "en"

    def test_latin_with_numbers_is_en(self):
        assert detect_query_language("VAT 15%") == "en"

    def test_return_values_are_literals(self):
        result = detect_query_language("hello")
        assert result in ("am", "en", "mixed")


class TestBuildE5QueryText:
    def test_no_category_returns_query_unchanged(self):
        result = build_e5_query_text("VAT rate?", taxpayer_category=None)
        assert result == "VAT rate?"

    def test_empty_category_returns_query_unchanged(self):
        result = build_e5_query_text("Question here", taxpayer_category="")
        assert result == "Question here"

    def test_whitespace_category_returns_query_unchanged(self):
        result = build_e5_query_text("Question here", taxpayer_category="  ")
        assert result == "Question here"

    def test_with_category_includes_both(self):
        result = build_e5_query_text("What is my tax?", taxpayer_category="small business")
        assert "small business" in result
        assert "What is my tax?" in result

    def test_empty_query_returns_empty(self):
        result = build_e5_query_text("", taxpayer_category="anything")
        assert result == ""

    def test_whitespace_query_returns_empty(self):
        result = build_e5_query_text("   ", taxpayer_category="cat")
        assert result == ""

    def test_category_comes_before_question(self):
        result = build_e5_query_text("My question", taxpayer_category="sme")
        assert result.index("sme") < result.index("My question")
