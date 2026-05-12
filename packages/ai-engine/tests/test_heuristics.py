"""Heuristic extraction tests."""

from ai_engine.heuristics import (
    guess_article_number_from_text,
    guess_proclamation_number,
)


def test_guess_proclamation() -> None:
    assert guess_proclamation_number("VAT Proclamation No. 285/2002") == "285/2002"


def test_guess_article() -> None:
    t = "Article 16\n\nThe registration threshold is one million birr."
    assert guess_article_number_from_text(t) == "16"
