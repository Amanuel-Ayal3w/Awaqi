"""
MoR (mor.gov.et) discovery and ingestion (AWA-5 / AWA-7 / AWA-11).

The Ministry site uses Liferay-style paths (document libraries, ``view_file`` URLs).
As of 2026, common entry points include:

- Homepage: ``https://mor.gov.et`` / ``https://www.mor.gov.et``
- Proclamations listing: ``https://www.mor.gov.et/web/mor/proclamations``
- Directives listing: ``https://www.mor.gov.et/web/mor/directives``

Site structure **changes over time** — verify URLs in a browser and override
``MOR_SCRAPE_SEED_URLS`` if listings move.

Configuration:

- ``MOR_SCRAPE_SEED_URLS``: comma-separated HTML pages to open first (PDF links and
  internal links are collected per depth settings).
- ``MOR_SCRAPE_MAX_DEPTH``: internal link follow depth (0 = seeds only; default ``1``
  = seeds + one hop).
- ``MOR_SCRAPE_MAX_PAGES``: max HTML pages fetched per run (budget for discovery).
- ``MOR_SCRAPE_MAX_LINKS``: max PDF URLs processed per run (download + ingest cap).

Registry dedup uses SHA256("url:size") and byte ``file_hash`` (AWA-7).
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentStatus
from sqlalchemy import select

from ai_engine.ingest import ingest_bytes_for_document
from ai_engine.scraper.http_retry import fetch_with_retry

logger = logging.getLogger(__name__)

USER_AGENT = os.getenv("MOR_SCRAPER_USER_AGENT", "AwaqiBot/1.0 (+https://github.com/aait/Awaqi)")
MAX_LINKS_PER_RUN = int(os.getenv("MOR_SCRAPE_MAX_LINKS", "30"))
MAX_PAGES_PER_RUN = int(os.getenv("MOR_SCRAPE_MAX_PAGES", "40"))
MAX_DEPTH = int(os.getenv("MOR_SCRAPE_MAX_DEPTH", "1"))

_DEFAULT_SEED_LIST = [
    "https://mor.gov.et",
    "https://www.mor.gov.et/web/mor/proclamations",
    "https://www.mor.gov.et/web/mor/directives",
]

DEFAULT_SEEDS = os.getenv(
    "MOR_SCRAPE_SEED_URLS",
    ",".join(_DEFAULT_SEED_LIST),
).split(",")

_SKIP_LINK_SUFFIXES = (
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".mjs",
    ".woff",
    ".woff2",
    ".ttf",
    ".zip",
    ".rar",
    ".mp4",
    ".mp3",
)


def _registry_key(url: str, size: int) -> str:
    return hashlib.sha256(f"{url}:{size}".encode("utf-8")).hexdigest()


def _trim_url(url: str, max_len: int = 160) -> str:
    u = url.strip()
    return u if len(u) <= max_len else u[: max_len - 3] + "..."


def _allowed_hosts_from_seeds(seeds: list[str]) -> set[str]:
    out: set[str] = set()
    for s in seeds:
        netloc = urlparse(s.strip()).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc:
            out.add(netloc)
    return out


def _host_allowed(url: str, allowed: set[str]) -> bool:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc in allowed


def _visit_key(url: str) -> str:
    """Normalize URL for visited-set (ignore fragment)."""
    p = urlparse(url)
    path = p.path if p.path else "/"
    return urlunparse(
        (
            p.scheme.lower(),
            p.netloc.lower(),
            path.rstrip("/") or "/",
            "",
            p.query,
            "",
        )
    )


def _extract_pdf_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        low = href.lower()
        if "mailto:" in low or low.startswith("javascript:"):
            continue
        joined = urljoin(base_url, href)
        if joined.lower().split("?", 1)[0].endswith(".pdf"):
            found.append(joined)
    return list(dict.fromkeys(found))


def _extract_same_site_html_links(html: str, base_url: str, allowed_hosts: set[str]) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        low = href.lower()
        if "mailto:" in low or low.startswith("javascript:") or low.startswith("#"):
            continue
        joined = urljoin(base_url, href)
        parsed = urlparse(joined)
        if parsed.scheme not in ("http", "https"):
            continue
        if not _host_allowed(joined, allowed_hosts):
            continue
        path_lower = (parsed.path or "").lower()
        query_lower = (parsed.query or "").lower()
        joined_lower = joined.lower()
        if joined_lower.split("?", 1)[0].endswith(".pdf"):
            continue
        if any(path_lower.endswith(s) or query_lower.endswith(s) for s in _SKIP_LINK_SUFFIXES):
            continue
        if any(joined_lower.endswith(s) for s in _SKIP_LINK_SUFFIXES):
            continue
        found.append(joined)
    return list(dict.fromkeys(found))


async def _discover_pdf_urls(client: httpx.AsyncClient) -> list[str]:
    seeds = [s.strip() for s in DEFAULT_SEEDS if s.strip()]
    if not seeds:
        return []

    allowed_hosts = _allowed_hosts_from_seeds(seeds)
    queue: deque[tuple[str, int]] = deque((u, 0) for u in seeds)
    visited: set[str] = set()
    pdf_urls: list[str] = []
    pages_fetched = 0

    while queue and pages_fetched < MAX_PAGES_PER_RUN:
        url, depth = queue.popleft()
        vk = _visit_key(url)
        if vk in visited:
            continue
        visited.add(vk)

        try:
            r = await fetch_with_retry(client, url)
            text = r.text
        except httpx.HTTPError:
            logger.warning(
                "scrape_seed_fetch_failed url=%s",
                _trim_url(url),
                exc_info=False,
            )
            continue

        pages_fetched += 1
        for p in _extract_pdf_links(text, url):
            if p not in pdf_urls:
                pdf_urls.append(p)
        if len(pdf_urls) >= MAX_LINKS_PER_RUN:
            return pdf_urls[:MAX_LINKS_PER_RUN]

        if depth < MAX_DEPTH:
            for link in _extract_same_site_html_links(text, url, allowed_hosts):
                lk = _visit_key(link)
                if lk not in visited:
                    queue.append((link, depth + 1))

    return list(dict.fromkeys(pdf_urls))[:MAX_LINKS_PER_RUN]


async def run_mor_scrape_cycle() -> dict[str, int]:
    """
    Fetch seed pages (and shallow internal links), discover PDFs, skip known
    ``registry_key`` / ``file_hash``, insert ``Document`` rows and run ingestion.
    """
    stats: dict[str, int] = {"inserted": 0, "skipped": 0, "errors": 0}
    seeds = [s.strip() for s in DEFAULT_SEEDS if s.strip()]
    if not seeds:
        logger.info("No MOR_SCRAPE_SEED_URLS configured; scrape cycle no-op")
        return stats

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(120.0, connect=30.0)
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(
        headers=headers,
        limits=limits,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        try:
            all_links = await _discover_pdf_urls(client)
        except Exception:
            logger.exception("discover_pdf_urls_failed")
            stats["errors"] += 1
            return stats

        for url in all_links:
            async with AsyncSessionLocal() as db:
                try:
                    r = await fetch_with_retry(client, url)
                    data = r.content
                    size = len(data)
                    rk = _registry_key(url, size)
                    fh = hashlib.sha256(data).hexdigest()

                    dup_rk = await db.execute(
                        select(Document.id).where(Document.registry_key == rk)
                    )
                    if dup_rk.scalar_one_or_none():
                        stats["skipped"] += 1
                        continue

                    dup_fh = await db.execute(
                        select(Document.id).where(Document.file_hash == fh)
                    )
                    if dup_fh.scalar_one_or_none():
                        stats["skipped"] += 1
                        continue

                    title = urlparse(url).path.rsplit("/", 1)[-1] or "document.pdf"
                    title = title[:512]
                    doc = Document(
                        id=uuid.uuid4(),
                        title=title,
                        source_url=url[:2048],
                        file_hash=fh,
                        registry_key=rk,
                        byte_size=size,
                        status=DocumentStatus.PENDING,
                    )
                    db.add(doc)
                    await db.commit()
                    await db.refresh(doc)

                    await ingest_bytes_for_document(
                        db,
                        doc,
                        data,
                        mime_type="application/pdf",
                        filename=title,
                        genai_client=None,
                    )
                    stats["inserted"] += 1
                except httpx.HTTPError:
                    logger.warning(
                        "scrape_pdf_fetch_failed url=%s",
                        _trim_url(url),
                        exc_info=False,
                    )
                    stats["errors"] += 1
                    await db.rollback()
                except Exception:
                    logger.exception("scrape_url_failed url=%s", _trim_url(url))
                    stats["errors"] += 1
                    await db.rollback()

    return stats
