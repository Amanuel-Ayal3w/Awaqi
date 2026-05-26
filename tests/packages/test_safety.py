"""Unit tests for the query safety gate (ai_engine.safety)."""

from ai_engine.safety import should_refuse_query


class TestShouldRefuseQuery:
    def test_empty_string_is_refused(self):
        refused, msg = should_refuse_query("")
        assert refused
        assert msg is not None

    def test_whitespace_only_is_refused(self):
        refused, msg = should_refuse_query("   ")
        assert refused
        assert msg is not None

    def test_profane_word_is_refused(self):
        refused, msg = should_refuse_query("fuck you")
        assert refused
        assert msg is not None
        assert "language" in msg.lower()

    def test_mixed_case_profanity_is_refused(self):
        refused, _ = should_refuse_query("FUCK off")
        assert refused

    def test_profanity_embedded_in_sentence_is_refused(self):
        refused, _ = should_refuse_query("what the shit is VAT?")
        assert refused

    def test_legitimate_tax_question_passes(self):
        refused, msg = should_refuse_query("What is the VAT rate in Ethiopia?")
        assert not refused
        assert msg is None

    def test_amharic_question_passes(self):
        refused, _ = should_refuse_query("ቀረጥ ምን ያህል ነው")
        assert not refused

    def test_very_short_gibberish_is_refused(self):
        refused, _ = should_refuse_query("!!!")
        assert refused

    def test_punctuation_only_is_refused(self):
        refused, _ = should_refuse_query("???")
        assert refused

    def test_single_letter_is_refused(self):
        refused, _ = should_refuse_query("x")
        assert refused

    def test_normal_short_question_passes(self):
        refused, _ = should_refuse_query("VAT rate?")
        assert not refused

    def test_none_like_empty_string_is_refused(self):
        refused, _ = should_refuse_query("")
        assert refused

    def test_return_type_is_tuple(self):
        result = should_refuse_query("Hello")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_passing_query_returns_none_message(self):
        _, msg = should_refuse_query("income tax filing deadline?")
        assert msg is None

    def test_profane_message_is_not_none(self):
        _, msg = should_refuse_query("shit")
        assert msg is not None
        assert isinstance(msg, str)
