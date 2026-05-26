"""Telegram channel scraper orchestration and config."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone

import uuid

from ai_engine.ingest import ingest_bytes_for_document
from ai_engine.scraper.storage import delete_storage_file, guess_media_type, read_document_file
from ai_engine.scraper.telegram_scraper import run_telegram_scrape_cycle
from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentChunk, DocumentStatus
from database.models.telegram import TelegramMessage, TelegramScrapeRun, TelegramScraperConfig
from sqlalchemy import delete, func, or_, select

logger = logging.getLogger(__name__)


@dataclass
class TelegramSettingsView:
    channel_username: str
    scrape_since: date
    max_messages_per_run: int
    scheduler_enabled: bool
    cron_hour: int
    cron_minute: int
    api_configured: bool
    session_configured: bool


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").lower()
    return raw in ("1", "true", "yes")


def _credentials_configured() -> tuple[bool, bool]:
    api_ok = bool(os.getenv("TELEGRAM_API_ID", "").strip()) and bool(
        os.getenv("TELEGRAM_API_HASH", "").strip()
    )
    session_ok = bool(os.getenv("TELEGRAM_SESSION_STRING", "").strip())
    return api_ok, session_ok


def _default_settings() -> TelegramSettingsView:
    api_ok, session_ok = _credentials_configured()
    return TelegramSettingsView(
        channel_username=os.getenv("TELEGRAM_CHANNEL", "morwestaa").lstrip("@"),
        scrape_since=date.fromisoformat(os.getenv("TELEGRAM_SCRAPE_SINCE", "2026-04-01")[:10]),
        max_messages_per_run=int(os.getenv("TELEGRAM_SCRAPE_MAX_MESSAGES", "200")),
        scheduler_enabled=_env_bool("TELEGRAM_SCHEDULER_ENABLED", False),
        cron_hour=int(os.getenv("TELEGRAM_CRON_HOUR", "1")),
        cron_minute=int(os.getenv("TELEGRAM_CRON_MINUTE", "0")),
        api_configured=api_ok,
        session_configured=session_ok,
    )


async def ensure_telegram_config_row() -> TelegramScraperConfig:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramScraperConfig).where(TelegramScraperConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return row
        defaults = _default_settings()
        row = TelegramScraperConfig(
            id=1,
            channel_username=defaults.channel_username,
            scrape_since=defaults.scrape_since,
            max_messages_per_run=defaults.max_messages_per_run,
            scheduler_enabled=defaults.scheduler_enabled,
            cron_hour=defaults.cron_hour,
            cron_minute=defaults.cron_minute,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


async def get_telegram_settings() -> TelegramSettingsView:
    defaults = _default_settings()
    try:
        row = await ensure_telegram_config_row()
    except Exception:
        logger.exception("telegram_config_load_failed")
        return defaults

    api_ok, session_ok = _credentials_configured()
    return TelegramSettingsView(
        channel_username=row.channel_username,
        scrape_since=row.scrape_since,
        max_messages_per_run=int(row.max_messages_per_run),
        scheduler_enabled=bool(row.scheduler_enabled),
        cron_hour=int(row.cron_hour),
        cron_minute=int(row.cron_minute),
        api_configured=api_ok,
        session_configured=session_ok,
    )


async def update_telegram_settings(
    *,
    channel_username: str | None = None,
    scrape_since: date | None = None,
    max_messages_per_run: int | None = None,
    scheduler_enabled: bool | None = None,
    cron_hour: int | None = None,
    cron_minute: int | None = None,
) -> TelegramSettingsView:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramScraperConfig).where(TelegramScraperConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            await ensure_telegram_config_row()
            result = await db.execute(
                select(TelegramScraperConfig).where(TelegramScraperConfig.id == 1)
            )
            row = result.scalar_one()

        if channel_username is not None:
            row.channel_username = channel_username.lstrip("@")
        if scrape_since is not None:
            row.scrape_since = scrape_since
        if max_messages_per_run is not None:
            row.max_messages_per_run = max_messages_per_run
        if scheduler_enabled is not None:
            row.scheduler_enabled = scheduler_enabled
        if cron_hour is not None:
            row.cron_hour = cron_hour
        if cron_minute is not None:
            row.cron_minute = cron_minute
        row.updated_at = datetime.now(timezone.utc)
        await db.commit()

    return await get_telegram_settings()


async def execute_telegram_scrape_run(trigger: str) -> dict[str, int]:
    settings = await get_telegram_settings()
    run_id = None
    async with AsyncSessionLocal() as db:
        run = TelegramScrapeRun(
            trigger=trigger,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    stats: dict[str, int] = {
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
    error_message: str | None = None
    status = "success"
    try:
        stats = await run_telegram_scrape_cycle(
            channel_username=settings.channel_username,
            scrape_since=settings.scrape_since,
            max_messages=settings.max_messages_per_run,
            run_id=run_id,
        )
    except Exception as e:
        logger.exception("telegram_scrape_run_failed trigger=%s", trigger)
        status = "failed"
        error_message = str(e)[:2000]
        stats["errors"] = stats.get("errors", 0) + 1

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramScrapeRun).where(TelegramScrapeRun.id == run_id)
        )
        run = result.scalar_one()
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        run.stats = stats
        run.error_message = error_message
        await db.commit()

    return stats


async def get_last_telegram_run() -> TelegramScrapeRun | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramScrapeRun)
            .order_by(TelegramScrapeRun.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def list_telegram_runs(limit: int = 20) -> list[TelegramScrapeRun]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramScrapeRun)
            .order_by(TelegramScrapeRun.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def list_telegram_messages(
    *,
    limit: int = 50,
    offset: int = 0,
    channel: str | None = None,
    message_type: str | None = None,
    document_status: str | None = None,
    ingest_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[tuple[TelegramMessage, str | None]], int]:
    """Return (message, document_status) rows."""
    async with AsyncSessionLocal() as db:
        filters = []
        if channel:
            filters.append(TelegramMessage.channel_username == channel.lstrip("@"))
        if message_type:
            filters.append(TelegramMessage.message_type == message_type)
        if search and search.strip():
            q = f"%{search.strip()}%"
            filters.append(
                or_(
                    TelegramMessage.text_preview.ilike(q),
                    TelegramMessage.file_name.ilike(q),
                )
            )
        if ingest_filter == "none":
            filters.append(TelegramMessage.document_id.is_(None))
        elif ingest_filter == "indexed":
            filters.append(Document.status == DocumentStatus.INDEXED.value)
        elif ingest_filter == "failed":
            filters.append(Document.status == DocumentStatus.FAILED.value)
        elif ingest_filter == "manual":
            filters.append(Document.status == DocumentStatus.REQUIRES_MANUAL_REVIEW.value)
        elif document_status:
            filters.append(Document.status == document_status)

        base = select(TelegramMessage, Document.status).outerjoin(
            Document, TelegramMessage.document_id == Document.id
        )
        if filters:
            base = base.where(*filters)

        count_stmt = select(func.count(TelegramMessage.id)).select_from(TelegramMessage)
        count_stmt = count_stmt.outerjoin(
            Document, TelegramMessage.document_id == Document.id
        )
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        stmt = base.order_by(TelegramMessage.posted_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        rows = [(msg, str(status) if status is not None else None) for msg, status in result.all()]
        return rows, total


async def get_telegram_message_row(
    message_row_id: uuid.UUID,
) -> tuple[TelegramMessage, str | None] | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramMessage, Document.status)
            .outerjoin(Document, TelegramMessage.document_id == Document.id)
            .where(TelegramMessage.id == message_row_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        msg, status = row
        return msg, str(status) if status is not None else None


async def _delete_document_full(db, doc: Document) -> None:
    delete_storage_file(doc.storage_path)
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    await db.delete(doc)


async def delete_telegram_message(
    message_row_id: uuid.UUID,
    *,
    delete_linked_document: bool = True,
) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramMessage).where(TelegramMessage.id == message_row_id)
        )
        msg = result.scalar_one_or_none()
        if msg is None:
            return False
        doc_id = msg.document_id
        await db.delete(msg)
        if delete_linked_document and doc_id:
            doc = await db.get(Document, doc_id)
            if doc is not None:
                await _delete_document_full(db, doc)
        await db.commit()
        return True


async def clear_telegram_messages(
    *,
    channel: str | None = None,
    delete_linked_documents: bool = True,
) -> int:
    """Remove tracked Telegram rows (and optionally linked documents) so scrape can re-run."""
    async with AsyncSessionLocal() as db:
        q = select(TelegramMessage)
        if channel:
            q = q.where(TelegramMessage.channel_username == channel.lstrip("@"))
        result = await db.execute(q)
        messages = list(result.scalars().all())
        doc_ids = {m.document_id for m in messages if m.document_id}
        for msg in messages:
            await db.delete(msg)
        if delete_linked_documents:
            for doc_id in doc_ids:
                doc = await db.get(Document, doc_id)
                if doc is not None and doc.source_system == "telegram":
                    await _delete_document_full(db, doc)
        await db.commit()
        return len(messages)


async def reingest_telegram_message(
    message_row_id: uuid.UUID,
    *,
    force_index: bool = False,
) -> str:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramMessage).where(TelegramMessage.id == message_row_id)
        )
        msg = result.scalar_one_or_none()
        if msg is None:
            raise LookupError("not_found")
        if not msg.document_id:
            raise ValueError("no_linked_document")
        doc = await db.get(Document, msg.document_id)
        if doc is None:
            raise ValueError("document_missing")
        file_bytes = read_document_file(doc.storage_path)
        if not file_bytes:
            raise ValueError("no_stored_file")
        mime = guess_media_type(doc.storage_path)
        filename = doc.storage_path or f"{doc.id}.bin"
        await ingest_bytes_for_document(
            db,
            doc,
            file_bytes,
            mime_type=mime,
            filename=filename,
            genai_client=None,
            force_index=force_index,
        )
        await db.refresh(doc)
        return str(getattr(doc.status, "value", doc.status))
