"""EthioData tax scraper: ingest digest text + linked law PDFs."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentStatus
from sqlalchemy import select

from ai_engine.ingest import ingest_bytes_for_document, ingest_plain_text
from ai_engine.scraper.http_retry import fetch_with_retry
from ai_engine.scraper.storage import save_document_file

logger = logging.getLogger(__name__)

ETHIODATA_TAG_URL = "https://ethiodata.et/tag/tax/"
SOURCE_SYSTEM_ETHIODATA = "ethiodata"


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else "item"
    clean = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    return clean or "item"


def _external_id(article_url: str, part: str) -> str:
    token = hashlib.sha256(article_url.encode("utf-8")).hexdigest()[:24]
    return f"ethiodata:{token}:{part}"


def _extract_article_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(ETHIODATA_TAG_URL, href)
        if "/tag/tax/" in full:
            continue
        if "ethiodata.et" not in full:
            continue
        if full.rstrip("/") == "https://ethiodata.et":
            continue
        if full not in links:
            links.append(full)
    return links


def _extract_digest_text(article_html: str) -> str:
    soup = BeautifulSoup(article_html, "lxml")
    article = soup.select_one("article") or soup.select_one("main") or soup
    parts: list[str] = []
    for node in article.select("h1,h2,h3,p,li"):
        text = node.get_text(" ", strip=True)
        if text:
            parts.append(text)
    digest = "\n".join(parts).strip()
    return digest[:60_000]


def _extract_pdf_link(article_url: str, article_html: str) -> str | None:
    soup = BeautifulSoup(article_html, "lxml")
    # Prefer explicit "download" link labels.
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        label = a.get_text(" ", strip=True).lower()
        if not href:
            continue
        full = urljoin(article_url, href)
        if full.lower().endswith(".pdf"):
            return full
        if "download" in label and "pdf" in label:
            return full
    # Fallback: regex any PDF URL in page source.
    hit = re.search(r"https?://[^\s\"']+\.pdf", article_html, flags=re.IGNORECASE)
    return hit.group(0) if hit else None


async def _find_document_by_external(db, external_id: str) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.source_system == SOURCE_SYSTEM_ETHIODATA,
            Document.external_id == external_id,
        )
    )
    return result.scalar_one_or_none()


async def _upsert_digest_doc(
    *,
    db,
    title: str,
    article_url: str,
    external_id: str,
    text: str,
) -> bool:
    encoded = text.encode("utf-8")
    file_hash = hashlib.sha256(encoded).hexdigest()
    existing = await _find_document_by_external(db, external_id)
    if existing and existing.file_hash == file_hash:
        return False

    if existing is None:
        doc = Document(
            id=uuid.uuid4(),
            title=f"{title} [digest]"[:512],
            source_url=article_url[:2048],
            file_hash=file_hash,
            byte_size=len(encoded),
            status=DocumentStatus.PENDING,
            source_system=SOURCE_SYSTEM_ETHIODATA,
            external_id=external_id,
            language="en",
        )
        db.add(doc)
        await db.flush()
    else:
        doc = existing
        doc.title = f"{title} [digest]"[:512]
        doc.source_url = article_url[:2048]
        doc.file_hash = file_hash
        doc.byte_size = len(encoded)
        doc.status = DocumentStatus.PENDING
        doc.ingest_error = None
        doc.processing_stage = None

    doc.storage_path = save_document_file(doc.id, encoded, "txt")
    await db.commit()
    await db.refresh(doc)
    await ingest_plain_text(db, doc, text)
    return True


async def _upsert_pdf_doc(
    *,
    db,
    title: str,
    pdf_url: str,
    external_id: str,
    data: bytes,
) -> bool:
    file_hash = hashlib.sha256(data).hexdigest()
    existing = await _find_document_by_external(db, external_id)
    if existing and existing.file_hash == file_hash:
        return False

    if existing is None:
        doc = Document(
            id=uuid.uuid4(),
            title=title[:512],
            source_url=pdf_url[:2048],
            file_hash=file_hash,
            byte_size=len(data),
            status=DocumentStatus.PENDING,
            source_system=SOURCE_SYSTEM_ETHIODATA,
            external_id=external_id,
            language="en",
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
    return True


async def run_ethiodata_scrape_cycle(
    *,
    max_articles: int = 20,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, int]:
    """Scrape EthioData tax tag pages and ingest digest + linked PDFs."""
    stats = {
        "discovered": 0,
        "inserted": 0,
        "skipped": 0,
        "errors": 0,
        "digest_inserted": 0,
        "pdf_inserted": 0,
    }
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, connect=20.0),
        headers={"User-Agent": "AwaqiBot/1.0 (+https://github.com/aait/Awaqi)"},
    ) as client:
        tag_res = await fetch_with_retry(client, ETHIODATA_TAG_URL)
        articles = _extract_article_links(tag_res.text)[:max_articles]
        stats["discovered"] = len(articles)
        for idx, article_url in enumerate(articles):
            if on_progress is not None:
                on_progress(idx + 1, len(articles), f"EthioData: {article_url}")
            try:
                article_res = await fetch_with_retry(client, article_url)
                html = article_res.text
                title = (
                    BeautifulSoup(html, "lxml").title.get_text(" ", strip=True)
                    if BeautifulSoup(html, "lxml").title
                    else _slug_from_url(article_url)
                )
                digest = _extract_digest_text(html)
                pdf_url = _extract_pdf_link(article_url, html)

                async with AsyncSessionLocal() as db:
                    digest_ok = False
                    if digest:
                        digest_ok = await _upsert_digest_doc(
                            db=db,
                            title=title,
                            article_url=article_url,
                            external_id=_external_id(article_url, "digest"),
                            text=digest,
                        )
                    pdf_ok = False
                    if pdf_url:
                        pdf_res = await fetch_with_retry(client, pdf_url)
                        pdf_ok = await _upsert_pdf_doc(
                            db=db,
                            title=title,
                            pdf_url=pdf_url,
                            external_id=_external_id(article_url, "pdf"),
                            data=pdf_res.content,
                        )
                    if digest_ok:
                        stats["digest_inserted"] += 1
                        stats["inserted"] += 1
                    if pdf_ok:
                        stats["pdf_inserted"] += 1
                        stats["inserted"] += 1
                    if not digest_ok and not pdf_ok:
                        stats["skipped"] += 1
            except Exception:
                logger.exception("ethiodata_item_failed url=%s", article_url)
                stats["errors"] += 1
    return stats
