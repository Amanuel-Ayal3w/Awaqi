"""Tests for Telegram message parsing helpers."""

from datetime import datetime, timezone

from ai_engine.scraper.telegram_parse import (
    build_title,
    classify_filename,
    classify_image,
    external_id,
    is_substantial_text,
    normalize_channel,
    telegram_post_url,
)


def test_normalize_channel():
    assert normalize_channel("@morwestaa") == "morwestaa"


def test_external_id_and_url():
    assert external_id("morwestaa", 42, "text") == "morwestaa:42:text"
    assert telegram_post_url("morwestaa", 42) == "https://t.me/morwestaa/42"


def test_classify_image():
    spec = classify_image("image/jpeg", "photo.jpg")
    assert spec is not None
    assert spec.content_part == "image"


def test_is_substantial_text():
    assert is_substantial_text("https://youtu.be/abc12345678")
    assert not is_substantial_text("hi")


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
