"""
Telegram public channel scraper (@morwestaa) via Telethon (MTProto).

**Why not the Bot API?** Bots cannot read arbitrary channel history. You need a
user/client session (API ID + hash from https://my.telegram.org) and Telethon.

Environment:
  TELEGRAM_API_ID, TELEGRAM_API_HASH — required
  TELEGRAM_SESSION_STRING — StringSession (recommended for servers)
  TELEGRAM_CHANNEL — default morwestaa
  TELEGRAM_SCRAPE_SINCE — ISO date, default 2026-04-01
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import date, datetime, time, timezone

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
    build_title,
    classify_filename,
    classify_mime,
    external_id,
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
        "unsupported": 0,
    }


async def _find_telegram_message(db, channel: str, message_id: int) -> TelegramMessage | None:
    result = await db.execute(
        select(TelegramMessage).where(
            TelegramMessage.channel_username == channel,
            TelegramMessage.message_id == message_id,
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


async def _ingest_attachment(
    *,
    db,
    channel: str,
    message_id: int,
    posted_at: datetime,
    caption: str | None,
    file_bytes: bytes,
    spec,
    run_id: uuid.UUID,
    stats: dict[str, int],
) -> TelegramMessage:
    ext_id = external_id(channel, message_id)
    fh = hashlib.sha256(file_bytes).hexdigest()
    title = build_title(
        channel=channel,
        message_id=message_id,
        posted_at=posted_at,
        text=caption,
        filename=spec.filename,
    )
    tg_url = telegram_post_url(channel, message_id)

    existing_msg = await _find_telegram_message(db, channel, message_id)
    existing_doc = await _find_document_by_external(db, ext_id)

    if existing_doc and existing_doc.file_hash == fh:
        stats["messages_skipped"] += 1
        if existing_msg is None:
            row = TelegramMessage(
                channel_username=channel,
                message_id=message_id,
                posted_at=posted_at,
                message_type=spec.message_type,
                text_preview=(caption or "")[:2000] or None,
                file_name=spec.filename,
                mime_type=spec.mime_type,
                byte_size=len(file_bytes),
                telegram_url=tg_url,
                document_id=existing_doc.id,
                scrape_run_id=run_id,
                skip_reason="unchanged",
            )
            db.add(row)
            await db.flush()
            return row
        existing_msg.skip_reason = "unchanged"
        existing_msg.scrape_run_id = run_id
        await db.flush()
        return existing_msg

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
            source_url=tg_url,
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

    if existing_msg is not None:
        existing_msg.document_id = doc.id
        existing_msg.message_type = spec.message_type
        existing_msg.text_preview = (caption or "")[:2000] or None
        existing_msg.file_name = spec.filename
        existing_msg.mime_type = spec.mime_type
        existing_msg.byte_size = len(file_bytes)
        existing_msg.telegram_url = tg_url
        existing_msg.scrape_run_id = run_id
        existing_msg.skip_reason = None
        await db.flush()
        return existing_msg

    row = TelegramMessage(
        channel_username=channel,
        message_id=message_id,
        posted_at=posted_at,
        message_type=spec.message_type,
        text_preview=(caption or "")[:2000] or None,
        file_name=spec.filename,
        mime_type=spec.mime_type,
        byte_size=len(file_bytes),
        telegram_url=tg_url,
        document_id=doc.id,
        scrape_run_id=run_id,
    )
    db.add(row)
    await db.flush()
    return row


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
    ext_id = external_id(channel, message_id)
    encoded = text.encode("utf-8")
    fh = hashlib.sha256(encoded).hexdigest()
    title = build_title(
        channel=channel,
        message_id=message_id,
        posted_at=posted_at,
        text=text,
        filename=None,
    )
    tg_url = telegram_post_url(channel, message_id)

    existing_msg = await _find_telegram_message(db, channel, message_id)
    existing_doc = await _find_document_by_external(db, ext_id)

    if existing_doc and existing_doc.file_hash == fh:
        stats["messages_skipped"] += 1
        if existing_msg:
            existing_msg.skip_reason = "unchanged"
            existing_msg.scrape_run_id = run_id
            await db.flush()
            return existing_msg

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
            source_url=tg_url,
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

    if existing_msg is not None:
        existing_msg.document_id = doc.id
        existing_msg.message_type = "text"
        existing_msg.text_preview = text[:2000]
        existing_msg.mime_type = "text/plain"
        existing_msg.byte_size = len(encoded)
        existing_msg.telegram_url = tg_url
        existing_msg.scrape_run_id = run_id
        existing_msg.skip_reason = None
        await db.flush()
        return existing_msg

    row = TelegramMessage(
        channel_username=channel,
        message_id=message_id,
        posted_at=posted_at,
        message_type="text",
        text_preview=text[:2000],
        mime_type="text/plain",
        byte_size=len(encoded),
        telegram_url=tg_url,
        document_id=doc.id,
        scrape_run_id=run_id,
    )
    db.add(row)
    await db.flush()
    return row


async def run_telegram_scrape_cycle(
    *,
    channel_username: str | None = None,
    scrape_since: date | str | None = None,
    max_messages: int | None = None,
    run_id: uuid.UUID,
) -> dict[str, int]:
    """
    Scrape channel posts from ``scrape_since`` through now (newest-first walk).
    """
    stats = _empty_stats()
    channel = normalize_channel(channel_username or DEFAULT_CHANNEL)
    since_dt = _parse_since(scrape_since)
    cap = max_messages if max_messages is not None else int(
        os.getenv("TELEGRAM_SCRAPE_MAX_MESSAGES", "200")
    )

    api_id, api_hash, session_string = _telegram_credentials()
    if not session_string:
        raise RuntimeError(
            "TELEGRAM_SESSION_STRING is required for server-side channel scraping. "
            "Generate one with: uv run python scripts/telegram_gen_session.py"
        )

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError("Telegram session is not authorized. Regenerate TELEGRAM_SESSION_STRING.")

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
            caption = (message.message or "").strip() or None

            try:
                async with AsyncSessionLocal() as db:
                    if message.file:
                        fname = None
                        mime = None
                        try:
                            if message.file.name:
                                fname = message.file.name
                            if message.file.mime_type:
                                mime = message.file.mime_type
                        except Exception:
                            pass
                        spec = classify_mime(mime, fname)
                        if spec is None:
                            stats["unsupported"] += 1
                            row = await _find_telegram_message(db, channel, message.id)
                            if row is None:
                                db.add(
                                    TelegramMessage(
                                        channel_username=channel,
                                        message_id=message.id,
                                        posted_at=posted_at,
                                        message_type="unsupported",
                                        text_preview=(caption or "")[:2000],
                                        file_name=fname,
                                        mime_type=mime,
                                        telegram_url=telegram_post_url(channel, message.id),
                                        scrape_run_id=run_id,
                                        skip_reason="unsupported_type",
                                    )
                                )
                                await db.commit()
                            stats["messages_skipped"] += 1
                            continue

                        if spec.message_type == "pdf":
                            stats["pdf_posts"] += 1
                        elif spec.message_type == "pptx":
                            stats["pptx_posts"] += 1

                        from io import BytesIO

                        buffer = BytesIO()
                        await message.download_media(file=buffer)
                        file_bytes = buffer.getvalue()
                        if not file_bytes:
                            stats["errors"] += 1
                            continue
                        await _ingest_attachment(
                            db=db,
                            channel=channel,
                            message_id=message.id,
                            posted_at=posted_at,
                            caption=caption,
                            file_bytes=file_bytes,
                            spec=spec,
                            run_id=run_id,
                            stats=stats,
                        )
                    elif caption and len(caption) >= 40:
                        stats["text_posts"] += 1
                        await _ingest_text_post(
                            db=db,
                            channel=channel,
                            message_id=message.id,
                            posted_at=posted_at,
                            text=caption,
                            run_id=run_id,
                            stats=stats,
                        )
                    else:
                        stats["messages_skipped"] += 1
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
