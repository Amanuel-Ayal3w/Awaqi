"""
MoR (mor.gov.et) discovery and ingestion (AWA-5 / AWA-7 / AWA-11).

Discovery uses the MoR JSON API (``/api/*-categories`` + ``/*-by-category/{id}``).
Seed URLs are frontend routes that map to API families — see ``mor_api.py``.

Configuration:

- ``MOR_SCRAPE_SEED_URLS``: comma-separated law listing page URLs (6 defaults).
- ``MOR_API_BASE_URL``: API base (default ``https://www.mor.gov.et/api``).
- ``MOR_SCRAPE_MAX_LINKS``: max PDFs downloaded + ingested per run.
- ``DOCUMENT_STORAGE_DIR``: where scraped PDF bytes are stored on disk.

Registry dedup: ``registry_key`` (url:size), ``file_hash`` (bytes), ``(source_system, external_id)``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from collections.abc import Callable

import httpx
from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentStatus
from sqlalchemy import select

from ai_engine.ingest import ingest_bytes_for_document
from ai_engine.scraper.http_retry import fetch_with_retry
from ai_engine.scraper.mor_api import (
    MorDiscoveredItem,
    default_seed_urls,
    discover_all_items,
)
from ai_engine.scraper.mor_http import create_mor_http_client
from ai_engine.scraper.storage import save_document_pdf

logger = logging.getLogger(__name__)
MAX_LINKS_PER_RUN = int(os.getenv("MOR_SCRAPE_MAX_LINKS", "30"))
SOURCE_SYSTEM_MOR = "mor"

_DEFAULT_SEED_LIST = default_seed_urls()

DEFAULT_SEEDS = os.getenv(
    "MOR_SCRAPE_SEED_URLS",
    ",".join(_DEFAULT_SEED_LIST),
).split(",")


def _registry_key(url: str, size: int) -> str:
    return hashlib.sha256(f"{url}:{size}".encode("utf-8")).hexdigest()


def _trim_url(url: str, max_len: int = 160) -> str:
    u = url.strip()
    return u if len(u) <= max_len else u[: max_len - 3] + "..."


def _proclamation_number_label(item: MorDiscoveredItem) -> str | None:
    if item.number is None:
        return None
    if item.year is not None:
        return f"{item.number}/{item.year}"
    return str(item.number)


def _title_with_metadata(item: MorDiscoveredItem) -> str:
    base = item.title
    num = _proclamation_number_label(item)
    if num and num not in base:
        return f"{base} ({num})"[:512]
    return base[:512]


async def _find_by_external_id(db, external_id: str) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.source_system == SOURCE_SYSTEM_MOR,
            Document.external_id == external_id,
        )
    )
    return result.scalar_one_or_none()


async def _should_skip_item(
    db,
    item: MorDiscoveredItem,
    file_hash: str,
    registry_key: str,
) -> tuple[bool, Document | None]:
    """Return (skip, existing_doc). Re-ingest when same external_id but hash changed."""
    existing_ext = await _find_by_external_id(db, item.external_id)
    if existing_ext is not None:
        if existing_ext.file_hash == file_hash:
            return True, existing_ext
        return False, existing_ext

    dup_rk = await db.execute(select(Document.id).where(Document.registry_key == registry_key))
    if dup_rk.scalar_one_or_none():
        return True, None

    dup_fh = await db.execute(select(Document.id).where(Document.file_hash == file_hash))
    if dup_fh.scalar_one_or_none():
        return True, None

    return False, None


async def run_mor_scrape_cycle(
    *,
    seed_urls: list[str] | None = None,
    max_links: int | None = None,
    on_progress: "Callable[[int, int, str], None] | None" = None,
) -> dict[str, int]:
    """
    Discover PDFs via MoR API, download new/changed files, persist to disk, ingest.

    Args:
        on_progress: Optional callback(current, total, step) called after each item.
    """
    stats: dict[str, int] = {
        "discovered": 0,
        "inserted": 0,
        "skipped": 0,
        "errors": 0,
    }
    raw_seeds = seed_urls if seed_urls is not None else DEFAULT_SEEDS
    seeds = [s.strip() for s in raw_seeds if s.strip()]
    link_cap = max_links if max_links is not None else MAX_LINKS_PER_RUN
    if not seeds:
        logger.info("No MOR_SCRAPE_SEED_URLS configured; scrape cycle no-op")
        return stats

    async with create_mor_http_client() as client:
        try:
            all_items = await discover_all_items(client, seeds)
        except Exception:
            logger.exception("mor_api_discover_failed")
            stats["errors"] += 1
            return stats

        stats["discovered"] = len(all_items)
        items_to_process = all_items[:link_cap]

        total_items = len(items_to_process)
        for idx, item in enumerate(items_to_process):
            if on_progress is not None:
                on_progress(idx, total_items, f"Fetching: {item.title[:60]}")
            async with AsyncSessionLocal() as db:
                try:
                    r = await fetch_with_retry(client, item.pdf_url)
                    data = r.content
                    size = len(data)
                    rk = _registry_key(item.pdf_url, size)
                    fh = hashlib.sha256(data).hexdigest()

                    skip, existing = await _should_skip_item(db, item, fh, rk)
                    if skip:
                        stats["skipped"] += 1
                        continue

                    title = _title_with_metadata(item)
                    proclamation_number = _proclamation_number_label(item)

                    if existing is not None:
                        doc = existing
                        doc.title = title
                        doc.source_url = item.pdf_url[:2048]
                        doc.file_hash = fh
                        doc.registry_key = rk
                        doc.byte_size = size
                        doc.proclamation_number = proclamation_number
                        doc.status = DocumentStatus.PENDING
                        doc.ingest_error = None
                        doc.processing_stage = None
                    else:
                        doc = Document(
                            id=uuid.uuid4(),
                            title=title,
                            source_url=item.pdf_url[:2048],
                            file_hash=fh,
                            registry_key=rk,
                            byte_size=size,
                            status=DocumentStatus.PENDING,
                            source_system=SOURCE_SYSTEM_MOR,
                            external_id=item.external_id,
                            proclamation_number=proclamation_number,
                            language="am",
                        )
                        db.add(doc)
                        await db.flush()

                    storage_rel = save_document_pdf(doc.id, data)
                    doc.storage_path = storage_rel
                    await db.commit()
                    await db.refresh(doc)

                    await ingest_bytes_for_document(
                        db,
                        doc,
                        data,
                        mime_type="application/pdf",
                        filename=f"{doc.id}.pdf",
                        genai_client=None,
                    )
                    stats["inserted"] += 1
                except httpx.HTTPError:
                    logger.warning(
                        "scrape_pdf_fetch_failed url=%s",
                        _trim_url(item.pdf_url),
                        exc_info=False,
                    )
                    stats["errors"] += 1
                    await db.rollback()
                except Exception:
                    logger.exception(
                        "scrape_item_failed external_id=%s url=%s",
                        item.external_id,
                        _trim_url(item.pdf_url),
                    )
                    stats["errors"] += 1
                    await db.rollback()

    return stats
