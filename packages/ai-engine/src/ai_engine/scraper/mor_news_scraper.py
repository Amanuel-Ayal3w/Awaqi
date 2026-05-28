"""MoR newspaper/magazine scraper for PDF ingestion."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections.abc import Callable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentStatus
from sqlalchemy import select

from ai_engine.ingest import ingest_bytes_for_document
from ai_engine.scraper.http_retry import fetch_with_retry
from ai_engine.scraper.mor_http import create_mor_http_client
from ai_engine.scraper.storage import save_document_file

logger = logging.getLogger(__name__)

SOURCE_SYSTEM_MOR_NEWS = "mor_news"
MOR_NEWS_PAGES = (
    "https://www.mor.gov.et/news-paper",
    "https://www.mor.gov.et/magazine",
)


def _normalize_pdf_url(base: str, href: str) -> str:
    full = urljoin(base, href.strip())
    if full.startswith("//"):
        full = f"https:{full}"
    return full


def _extract_pdf_links(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        full = _normalize_pdf_url(page_url, href)
        if ".pdf" in full.lower() and full not in links:
            links.append(full)
    # fallback: raw URL extraction from script blobs
    for hit in re.findall(r"https?://[^\s\"']+\.pdf", html, flags=re.IGNORECASE):
        if hit not in links:
            links.append(hit)
    return links


def _external_id_from_pdf_url(url: str) -> str:
    token = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return f"mor_news:{token}"


async def _find_by_external(db, external_id: str) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.source_system == SOURCE_SYSTEM_MOR_NEWS,
            Document.external_id == external_id,
        )
    )
    return result.scalar_one_or_none()


async def run_mor_news_scrape_cycle(
    *,
    max_links: int = 50,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, int]:
    """Download/ingest PDF links from MoR newspaper and magazine pages."""
    stats = {"discovered": 0, "inserted": 0, "skipped": 0, "errors": 0}
    async with create_mor_http_client() as client:
        pdf_links: list[str] = []
        for page in MOR_NEWS_PAGES:
            try:
                res = await fetch_with_retry(client, page)
                for link in _extract_pdf_links(page, res.text):
                    if link not in pdf_links:
                        pdf_links.append(link)
            except (httpx.HTTPError, ValueError, OSError):
                logger.exception("mor_news_page_fetch_failed page=%s", page)
                stats["errors"] += 1
        pdf_links = pdf_links[:max_links]
        stats["discovered"] = len(pdf_links)

        for idx, pdf_url in enumerate(pdf_links):
            if on_progress is not None:
                on_progress(idx + 1, len(pdf_links), f"MoR News: {pdf_url}")
            try:
                res = await fetch_with_retry(client, pdf_url)
                data = res.content
                file_hash = hashlib.sha256(data).hexdigest()
                external_id = _external_id_from_pdf_url(pdf_url)
                async with AsyncSessionLocal() as db:
                    existing = await _find_by_external(db, external_id)
                    if existing and existing.file_hash == file_hash:
                        stats["skipped"] += 1
                        continue
                    title = pdf_url.rsplit("/", 1)[-1] or "MoR newspaper PDF"
                    if existing is None:
                        doc = Document(
                            id=uuid.uuid4(),
                            title=title[:512],
                            source_url=pdf_url[:2048],
                            file_hash=file_hash,
                            byte_size=len(data),
                            status=DocumentStatus.PENDING,
                            source_system=SOURCE_SYSTEM_MOR_NEWS,
                            external_id=external_id,
                            language="am",
                        )
                        db.add(doc)
                        await db.flush()
                    else:
                        doc = existing
                        doc.title = title[:512]
                        doc.source_url = pdf_url[:2048]
                        doc.file_hash = file_hash
                        doc.byte_size = len(data)
                        doc.status = DocumentStatus.PENDING
                        doc.ingest_error = None
                        doc.processing_stage = None

                    doc.storage_path = save_document_file(doc.id, data, "pdf")
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
            except (httpx.HTTPError, ValueError, OSError):
                logger.exception("mor_news_pdf_ingest_failed url=%s", pdf_url)
                stats["errors"] += 1
    return stats
