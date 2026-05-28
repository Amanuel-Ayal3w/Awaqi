"""Helpers for Telegram channel message classification and metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

SOURCE_SYSTEM_TELEGRAM = "telegram"

MIN_TELEGRAM_TEXT_CHARS = 15

# ── Image relevance thresholds ────────────────────────────────────────────────
# Images below MIN_IMAGE_SIZE_BYTES are almost certainly icons / emoji /
# thumbnails — skip OCR entirely.
MIN_IMAGE_SIZE_BYTES: int = 15_000

# After OCR: require at least this many recognised words.
MIN_IMAGE_WORDS: int = 8

# After OCR: require this mean Tesseract confidence (0.0–1.0).
MIN_IMAGE_CONFIDENCE: float = 0.20

DOCUMENT_EXTENSIONS = {".pdf", ".pptx", ".docx", ".txt"}
IMAGE_MIMES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)


@dataclass(frozen=True)
class TelegramAttachmentSpec:
    message_type: str
    mime_type: str
    extension: str
    filename: str | None
    content_part: str


def normalize_channel(username: str) -> str:
    return username.strip().lstrip("@").lower()


def telegram_post_url(channel: str, message_id: int) -> str:
    ch = normalize_channel(channel)
    return f"https://t.me/{ch}/{message_id}"


def external_id(channel: str, message_id: int, content_part: str) -> str:
    return f"{normalize_channel(channel)}:{message_id}:{content_part}"


def is_substantial_text(text: str | None) -> bool:
    return bool(text and len(text.strip()) >= MIN_TELEGRAM_TEXT_CHARS)


def classify_filename(name: str | None) -> TelegramAttachmentSpec | None:
    if not name:
        return None
    lower = name.lower()
    for ext in DOCUMENT_EXTENSIONS:
        if lower.endswith(ext):
            mt = {
                ".pdf": "application/pdf",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".txt": "text/plain",
            }[ext]
            part = ext.lstrip(".")
            return TelegramAttachmentSpec(
                message_type=part,
                mime_type=mt,
                extension=part,
                filename=name,
                content_part=part,
            )
    return None


def classify_image(mime: str | None, filename: str | None = None) -> TelegramAttachmentSpec | None:
    mt = (mime or "").split(";")[0].strip().lower()
    if mt in IMAGE_MIMES or (filename and filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
        ext = "jpg"
        if mt == "image/png" or (filename and filename.lower().endswith(".png")):
            ext = "png"
        elif mt == "image/webp" or (filename and filename.lower().endswith(".webp")):
            ext = "webp"
        return TelegramAttachmentSpec(
            message_type="image",
            mime_type=mt or f"image/{ext}",
            extension=ext,
            filename=filename,
            content_part="image",
        )
    return None


def classify_mime(mime: str | None, filename: str | None = None) -> TelegramAttachmentSpec | None:
    img = classify_image(mime, filename)
    if img:
        return img
    by_name = classify_filename(filename)
    if by_name:
        return by_name
    if not mime:
        return None
    mt = mime.split(";")[0].strip().lower()
    mapping = {
        "application/pdf": ("pdf", "pdf", "pdf"),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
            "pptx",
            "pptx",
            "pptx",
        ),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
            "docx",
            "docx",
            "docx",
        ),
        "text/plain": ("text", "txt", "text"),
    }
    hit = mapping.get(mt)
    if not hit:
        return None
    message_type, ext, part = hit
    return TelegramAttachmentSpec(
        message_type=message_type,
        mime_type=mt,
        extension=ext,
        filename=filename,
        content_part=part,
    )


def should_ingest_image(file_bytes: bytes) -> tuple[bool, str]:
    """
    Decide whether a Telegram image is worth ingesting.

    Two-gate approach (fast → slow):
      1. File-size gate — tiny images (< MIN_IMAGE_SIZE_BYTES) are icons /
         thumbnails / emoji replacements; skip without running OCR.
      2. OCR content gate — run Tesseract and reject images that yield
         fewer than MIN_IMAGE_WORDS words or mean confidence < MIN_IMAGE_CONFIDENCE.

    Returns:
        (True, "")               — proceed with ingest
        (False, skip_reason)     — skip; skip_reason is a short string suitable
                                   for TelegramMessage.skip_reason
    """
    if len(file_bytes) < MIN_IMAGE_SIZE_BYTES:
        return False, "image_too_small"

    try:
        from ai_engine.document_processor import ocr_image_bytes

        text, confidence = ocr_image_bytes(file_bytes)
        words = text.split()
        if len(words) < MIN_IMAGE_WORDS:
            return False, f"image_no_text({len(words)}w)"
        if confidence < MIN_IMAGE_CONFIDENCE:
            return False, f"image_low_confidence({confidence:.2f})"
    except Exception:
        # If OCR crashes (missing tesseract, etc.) let it through — the
        # ingest pipeline will handle it gracefully.
        return True, ""

    return True, ""


def detect_unsupported_media_label(mime: str | None, message) -> str:
    """Human-readable label for non-ingested media (video, sticker, etc.)."""
    mt = (mime or "").split(";")[0].strip().lower()
    if message.video or mt.startswith("video/"):
        return "video"
    if message.voice or mt.startswith("audio/"):
        return "audio"
    if message.sticker:
        return "sticker"
    if mt:
        return mt.split("/")[0]
    return "media"


def build_title(
    *,
    channel: str,
    message_id: int,
    posted_at: datetime,
    text: str | None,
    filename: str | None,
    suffix: str | None = None,
) -> str:
    base = (text or "").strip().replace("\n", " ")
    if base:
        cleaned = re.sub(r"\s+", " ", base)
        if len(cleaned) > 120:
            cleaned = cleaned[:117] + "..."
        title = cleaned[:512]
    elif filename:
        title = f"@{normalize_channel(channel)} — {filename}"[:512]
    else:
        title = f"@{normalize_channel(channel)} post {message_id} ({posted_at.date().isoformat()})"[
            :512
        ]
    if suffix and suffix not in title:
        return f"{title} [{suffix}]"[:512]
    return title
