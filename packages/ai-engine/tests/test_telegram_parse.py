"""Tests for Telegram message parsing helpers."""

from datetime import datetime, timezone

from ai_engine.scraper.telegram_parse import (
    build_title,
    classify_filename,
    external_id,
    normalize_channel,
    telegram_post_url,
)


def test_normalize_channel():
    assert normalize_channel("@morwestaa") == "morwestaa"


def test_external_id_and_url():
    assert external_id("morwestaa", 42) == "morwestaa:42"
    assert telegram_post_url("morwestaa", 42) == "https://t.me/morwestaa/42"


def test_classify_pdf():
    spec = classify_filename("directive.pdf")
    assert spec is not None
    assert spec.message_type == "pdf"
    assert spec.extension == "pdf"


def test_classify_pptx():
    spec = classify_filename("training.pptx")
    assert spec is not None
    assert spec.message_type == "pptx"


def test_build_title_from_text():
    title = build_title(
        channel="morwestaa",
        message_id=1,
        posted_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
        text="የግብር ማስታወሻ ለ ነጋዴዎች",
        filename=None,
    )
    assert "የግብር" in title
