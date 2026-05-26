"""Helpers for Telegram channel message classification and metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


SOURCE_SYSTEM_TELEGRAM = "telegram"

SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".txt"}


@dataclass(frozen=True)
class TelegramAttachmentSpec:
    message_type: str
    mime_type: str
    extension: str
    filename: str | None


def normalize_channel(username: str) -> str:
    return username.strip().lstrip("@").lower()


def telegram_post_url(channel: str, message_id: int) -> str:
    ch = normalize_channel(channel)
    return f"https://t.me/{ch}/{message_id}"


def external_id(channel: str, message_id: int) -> str:
    return f"{normalize_channel(channel)}:{message_id}"


def classify_filename(name: str | None) -> TelegramAttachmentSpec | None:
    if not name:
        return None
    lower = name.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if lower.endswith(ext):
            mt = {
                ".pdf": "application/pdf",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".txt": "text/plain",
            }[ext]
            return TelegramAttachmentSpec(
                message_type=ext.lstrip("."),
                mime_type=mt,
                extension=ext.lstrip("."),
                filename=name,
            )
    return None


def classify_mime(mime: str | None, filename: str | None = None) -> TelegramAttachmentSpec | None:
    by_name = classify_filename(filename)
    if by_name:
        return by_name
    if not mime:
        return None
    mt = mime.split(";")[0].strip().lower()
    mapping = {
        "application/pdf": ("pdf", "pdf"),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
            "pptx",
            "pptx",
        ),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
            "docx",
            "docx",
        ),
        "text/plain": ("text", "txt"),
    }
    hit = mapping.get(mt)
    if not hit:
        return None
    message_type, ext = hit
    return TelegramAttachmentSpec(
        message_type=message_type,
        mime_type=mt,
        extension=ext,
        filename=filename,
    )


def build_title(
    *,
    channel: str,
    message_id: int,
    posted_at: datetime,
    text: str | None,
    filename: str | None,
) -> str:
    base = (text or "").strip().replace("\n", " ")
    if base:
        cleaned = re.sub(r"\s+", " ", base)
        if len(cleaned) > 120:
            cleaned = cleaned[:117] + "..."
        return cleaned[:512]
    if filename:
        return f"@{normalize_channel(channel)} — {filename}"[:512]
    return f"@{normalize_channel(channel)} post {message_id} ({posted_at.date().isoformat()})"[
        :512
    ]
