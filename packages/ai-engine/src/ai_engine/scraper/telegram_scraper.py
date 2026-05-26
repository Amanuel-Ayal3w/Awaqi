"""
Telegram public channel scraper (@morwestaa) via Telethon (MTProto).

Each Telegram post may yield **multiple** tracked rows / documents:
  - ``text`` — caption/body (always ingested when substantial)
  - ``pdf`` / ``pptx`` / ``docx`` — file attachments
  - ``image`` — photos OCR'd via Tesseract
  - ``video`` / ``unsupported`` — tracked but not indexed (e.g. YouTube previews)
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import date, datetime, time, timezone
from io import BytesIO

from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentStatus
from database.models.telegram import TelegramMessage, TelegramScrapeRun
from sqlalchemy import select
from telethon import TelegramClient
from telethon.sessions import StringSession

from ai_engine.ingest import ingest_bytes_for_document
from ai_engine.scraper.storage import save_document_file
from ai_engine.scraper.telegram_parse import (
    SOURCE_SYSTEM_TELEGRAM,
    TelegramAttachmentSpec,
    build_title,
    classify_image,
    classify_mime,
    detect_unsupported_media_label,
    external_id,
    is_substantial_text,
    normalize_channel,
    telegram_post_url,
)

logger = logging.getLogger(__name__)

DEFAULT_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "morwestaa")
DEFAULT_SINCE = os.getenv("TELEGRAM_SCRAPE_SINCE", "2026-04-01")


def _parse_since(value: date | str | None) -> datetime:
    if value is None:
        raw = DEFAULT_SINCE
    elif isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    else:
        raw = str(value)
    parsed = date.fromisoformat(raw[:10])
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def _telegram_credentials() -> tuple[int, str, str | None]:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    session = os.getenv("TELEGRAM_SESSION_STRING", "").strip() or None
    if not api_id or not api_hash:
        raise RuntimeError(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH are required. "
            "Create an app at https://my.telegram.org/apps"
        )
    return int(api_id), api_hash, session


def _empty_stats() -> dict[str, int]:
    return {
        "messages_seen": 0,
        "messages_skipped": 0,
        "documents_inserted": 0,
        "documents_updated": 0,
        "errors": 0,
        "text_posts": 0,
        "pdf_posts": 0,
        "pptx_posts": 0,
        "image_posts": 0,
        "unsupported": 0,
    }


async def _find_telegram_message(
    db, channel: str, message_id: int, content_part: str
) -> TelegramMessage | None:
    result = await db.execute(
        select(TelegramMessage).where(
            TelegramMessage.channel_username == channel,
            TelegramMessage.message_id == message_id,
            TelegramMessage.content_part == content_part,
        )
    )
    return result.scalar_one_or_none()


async def _find_document_by_external(db, ext_id: str) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.source_system == SOURCE_SYSTEM_TELEGRAM,
            Document.external_id == ext_id,
        )
    )
    return result.scalar_one_or_none()


async def _upsert_telegram_row(
    *,
    db,
    channel: str,
    message_id: int,
    posted_at: datetime,
    content_part: str,
    message_type: str,
    text_preview: str | None,
    file_name: str | None,
    mime_type: str | None,
    byte_size: int | None,
    document_id: uuid.UUID | None,
    run_id: uuid.UUID,
    skip_reason: str | None,
) -> TelegramMessage:
    row = await _find_telegram_message(db, channel, message_id, content_part)
    tg_url = telegram_post_url(channel, message_id)
    if row is None:
        row = TelegramMessage(
            channel_username=channel,
            message_id=message_id,
            posted_at=posted_at,
            content_part=content_part,
            message_type=message_type,
            text_preview=(text_preview or "")[:2000] or None,
            file_name=file_name,
            mime_type=mime_type,
            byte_size=byte_size,
            telegram_url=tg_url,
            document_id=document_id,
            scrape_run_id=run_id,
            skip_reason=skip_reason,
        )
        db.add(row)
    else:
        row.message_type = message_type
        row.text_preview = (text_preview or "")[:2000] or None
        row.file_name = file_name
        row.mime_type = mime_type
        row.byte_size = byte_size
        row.document_id = document_id
        row.scrape_run_id = run_id
        row.skip_reason = skip_reason
    await db.flush()
    return row


async def _ingest_bytes_as_document(
    *,
    db,
    channel: str,
    message_id: int,
    posted_at: datetime,
    content_part: str,
    file_bytes: bytes,
    spec: TelegramAttachmentSpec,
    caption: str | None,
    run_id: uuid.UUID,
    stats: dict[str, int],
) -> TelegramMessage:
    ext_id = external_id(channel, message_id, content_part)
    fh = hashlib.sha256(file_bytes).hexdigest()
    title = build_title(
        channel=channel,
        message_id=message_id,
        posted_at=posted_at,
        text=caption,
        filename=spec.filename,
        suffix=content_part,
    )
    existing_doc = await _find_document_by_external(db, ext_id)

    if existing_doc and existing_doc.file_hash == fh:
        stats["messages_skipped"] += 1
        return await _upsert_telegram_row(
            db=db,
            channel=channel,
            message_id=message_id,
            posted_at=posted_at,
            content_part=content_part,
            message_type=spec.message_type,
            text_preview=caption,
            file_name=spec.filename,
            mime_type=spec.mime_type,
            byte_size=len(file_bytes),
            document_id=existing_doc.id,
            run_id=run_id,
            skip_reason="unchanged",
        )

    if existing_doc is not None:
        doc = existing_doc
        doc.title = title
        doc.file_hash = fh
        doc.byte_size = len(file_bytes)
        doc.status = DocumentStatus.PENDING
        doc.ingest_error = None
        doc.processing_stage = None
        stats["documents_updated"] += 1
    else:
        doc = Document(
            id=uuid.uuid4(),
            title=title,
            source_url=telegram_post_url(channel, message_id),
            file_hash=fh,
            byte_size=len(file_bytes),
            status=DocumentStatus.PENDING,
            source_system=SOURCE_SYSTEM_TELEGRAM,
            external_id=ext_id,
            language="am",
        )
        db.add(doc)
        await db.flush()
        stats["documents_inserted"] += 1

    doc.storage_path = save_document_file(doc.id, file_bytes, spec.extension)
    await db.commit()
    await db.refresh(doc)

    await ingest_bytes_for_document(
        db,
        doc,
        file_bytes,
        mime_type=spec.mime_type,
        filename=spec.filename or f"{doc.id}.{spec.extension}",
        genai_client=None,
    )

    return await _upsert_telegram_row(
        db=db,
        channel=channel,
        message_id=message_id,
        posted_at=posted_at,
        content_part=content_part,
        message_type=spec.message_type,
        text_preview=caption,
        file_name=spec.filename,
        mime_type=spec.mime_type,
        byte_size=len(file_bytes),
        document_id=doc.id,
        run_id=run_id,
        skip_reason=None,
    )


async def _ingest_text_post(
    *,
    db,
    channel: str,
    message_id: int,
    posted_at: datetime,
    text: str,
    run_id: uuid.UUID,
    stats: dict[str, int],
) -> TelegramMessage:
    content_part = "text"
    ext_id = external_id(channel, message_id, content_part)
    encoded = text.encode("utf-8")
    fh = hashlib.sha256(encoded).hexdigest()
    title = build_title(
        channel=channel,
        message_id=message_id,
        posted_at=posted_at,
        text=text,
        filename=None,
    )
    existing_doc = await _find_document_by_external(db, ext_id)

    if existing_doc and existing_doc.file_hash == fh:
        stats["messages_skipped"] += 1
        return await _upsert_telegram_row(
            db=db,
            channel=channel,
            message_id=message_id,
            posted_at=posted_at,
            content_part=content_part,
            message_type="text",
            text_preview=text,
            file_name=None,
            mime_type="text/plain",
            byte_size=len(encoded),
            document_id=existing_doc.id,
            run_id=run_id,
            skip_reason="unchanged",
        )

    if existing_doc is not None:
        doc = existing_doc
        doc.title = title
        doc.file_hash = fh
        doc.byte_size = len(encoded)
        doc.status = DocumentStatus.PENDING
        stats["documents_updated"] += 1
    else:
        doc = Document(
            id=uuid.uuid4(),
            title=title,
            source_url=telegram_post_url(channel, message_id),
            file_hash=fh,
            byte_size=len(encoded),
            status=DocumentStatus.PENDING,
            source_system=SOURCE_SYSTEM_TELEGRAM,
            external_id=ext_id,
            language="am",
        )
        db.add(doc)
        await db.flush()
        stats["documents_inserted"] += 1

    doc.storage_path = save_document_file(doc.id, encoded, "txt")
    await db.commit()
    await db.refresh(doc)

    await ingest_bytes_for_document(
        db,
        doc,
        encoded,
        mime_type="text/plain",
        filename=f"{doc.id}.txt",
        genai_client=None,
    )

    return await _upsert_telegram_row(
        db=db,
        channel=channel,
        message_id=message_id,
        posted_at=posted_at,
        content_part=content_part,
        message_type="text",
        text_preview=text,
        file_name=None,
        mime_type="text/plain",
        byte_size=len(encoded),
        document_id=doc.id,
        run_id=run_id,
        skip_reason=None,
    )


async def _record_unsupported_media(
    *,
    db,
    channel: str,
    message_id: int,
    posted_at: datetime,
    caption: str | None,
    media_label: str,
    file_name: str | None,
    mime_type: str | None,
    run_id: uuid.UUID,
) -> None:
    content_part = media_label if media_label in ("video", "audio", "sticker") else "unsupported"
    await _upsert_telegram_row(
        db=db,
        channel=channel,
        message_id=message_id,
        posted_at=posted_at,
        content_part=content_part,
        message_type=media_label,
        text_preview=caption,
        file_name=file_name,
        mime_type=mime_type,
        byte_size=None,
        document_id=None,
        run_id=run_id,
        skip_reason="not_indexed",
    )


def _file_meta(message) -> tuple[str | None, str | None]:
    fname: str | None = None
    mime: str | None = None
    try:
        if message.file:
            if getattr(message.file, "name", None):
                fname = message.file.name
            if getattr(message.file, "mime_type", None):
                mime = message.file.mime_type
    except Exception:
        pass
    if message.photo and not mime:
        mime = "image/jpeg"
        fname = fname or "photo.jpg"
    return fname, mime


async def _process_message(
    *,
    db,
    message,
    channel: str,
    posted_at: datetime,
    run_id: uuid.UUID,
    stats: dict[str, int],
) -> None:
    caption = (message.message or "").strip() or None
    did_anything = False

    if is_substantial_text(caption):
        await _ingest_text_post(
            db=db,
            channel=channel,
            message_id=message.id,
            posted_at=posted_at,
            text=caption or "",
            run_id=run_id,
            stats=stats,
        )
        stats["text_posts"] += 1
        did_anything = True
    elif caption:
        await _ingest_text_post(
            db=db,
            channel=channel,
            message_id=message.id,
            posted_at=posted_at,
            text=caption,
            run_id=run_id,
            stats=stats,
        )
        stats["text_posts"] += 1
        did_anything = True

    has_media = bool(message.file or message.photo or message.video)
    if not has_media:
        if not did_anything:
            stats["messages_skipped"] += 1
        return

    fname, mime = _file_meta(message)
    spec = classify_mime(mime, fname)
    if spec is None and message.photo:
        spec = classify_image(mime or "image/jpeg", fname)

    if spec is None:
        label = detect_unsupported_media_label(mime, message)
        await _record_unsupported_media(
            db=db,
            channel=channel,
            message_id=message.id,
            posted_at=posted_at,
            caption=caption,
            media_label=label,
            file_name=fname,
            mime_type=mime,
            run_id=run_id,
        )
        stats["unsupported"] += 1
        return

    buffer = BytesIO()
    await message.download_media(file=buffer)
    file_bytes = buffer.getvalue()
    if not file_bytes:
        stats["errors"] += 1
        return

    if spec.message_type == "pdf":
        stats["pdf_posts"] += 1
    elif spec.message_type == "pptx":
        stats["pptx_posts"] += 1
    elif spec.message_type == "image":
        stats["image_posts"] += 1

    await _ingest_bytes_as_document(
        db=db,
        channel=channel,
        message_id=message.id,
        posted_at=posted_at,
        content_part=spec.content_part,
        file_bytes=file_bytes,
        spec=spec,
        caption=caption,
        run_id=run_id,
        stats=stats,
    )


async def run_telegram_scrape_cycle(
    *,
    channel_username: str | None = None,
    scrape_since: date | str | None = None,
    max_messages: int | None = None,
    run_id: uuid.UUID,
) -> dict[str, int]:
    """Scrape channel posts from ``scrape_since`` through now (newest-first walk)."""
    stats = _empty_stats()
    channel = normalize_channel(channel_username or DEFAULT_CHANNEL)
    since_dt = _parse_since(scrape_since)
    cap = max_messages if max_messages is not None else int(
        os.getenv("TELEGRAM_SCRAPE_MAX_MESSAGES", "200")
    )

    api_id, api_hash, session_string = _telegram_credentials()
    if not session_string:
        raise RuntimeError(
            "TELEGRAM_SESSION_STRING is required. "
            "Generate: uv run python scripts/telegram_gen_session.py"
        )

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError("Telegram session not authorized.")

    try:
        entity = await client.get_entity(channel)
        async for message in client.iter_messages(entity, limit=None):
            if stats["messages_seen"] >= cap:
                break
            if message.date is None:
                continue
            posted_at = message.date
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            else:
                posted_at = posted_at.astimezone(timezone.utc)
            if posted_at < since_dt:
                break

            stats["messages_seen"] += 1
            try:
                async with AsyncSessionLocal() as db:
                    await _process_message(
                        db=db,
                        message=message,
                        channel=channel,
                        posted_at=posted_at,
                        run_id=run_id,
                        stats=stats,
                    )
                    await db.commit()
            except Exception:
                logger.exception(
                    "telegram_message_failed channel=%s msg_id=%s",
                    channel,
                    message.id,
                )
                stats["errors"] += 1
    finally:
        await client.disconnect()

    return stats
