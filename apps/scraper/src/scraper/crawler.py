"""Discover and download PDF files from the mor.gov.et REST API."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from scraper.config import (
    API_ENDPOINTS,
    HTTP_TIMEOUT,
    HTTP_USER_AGENT,
    MOR_API_BASE,
    VERIFY_SSL,
)

logger = logging.getLogger(__name__)


@dataclass
class PdfInfo:
    """Metadata for a discovered PDF before downloading."""

    url: str
    title: str
    source_endpoint: str


async def _fetch_endpoint(
    client: httpx.AsyncClient,
    endpoint: str,
) -> list[PdfInfo]:
    """Fetch a single API endpoint and extract PDF entries."""
    url = f"{MOR_API_BASE}{endpoint}"
    logger.info("Fetching %s", url)
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return []
    except Exception as exc:
        logger.error("Failed to parse JSON from %s: %s", url, exc)
        return []

    if not isinstance(data, list):
        logger.warning("Unexpected response type from %s: %s", url, type(data))
        return []

    results: list[PdfInfo] = []
    for item in data:
        pdf_url = item.get("pdfFile")
        title = item.get("title", "Untitled")
        if not pdf_url:
            continue
        results.append(
            PdfInfo(url=pdf_url, title=title, source_endpoint=endpoint)
        )

    logger.info("Found %d PDF(s) from %s", len(results), endpoint)
    return results


async def discover_all_pdfs(
    client: httpx.AsyncClient | None = None,
) -> list[PdfInfo]:
    """Query all MoR API endpoints and return a de-duplicated list of PDFs."""
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": HTTP_USER_AGENT},
            verify=VERIFY_SSL,
        )

    all_pdfs: list[PdfInfo] = []
    seen_urls: set[str] = set()

    try:
        for endpoint in API_ENDPOINTS:
            pdfs = await _fetch_endpoint(client, endpoint)
            for pdf in pdfs:
                if pdf.url not in seen_urls:
                    seen_urls.add(pdf.url)
                    all_pdfs.append(pdf)
    finally:
        if own_client:
            await client.aclose()

    logger.info("Total unique PDFs discovered: %d", len(all_pdfs))
    return all_pdfs


async def download_pdf(
    client: httpx.AsyncClient,
    pdf: PdfInfo,
) -> bytes | None:
    """Download a PDF and return the raw bytes, or None on failure."""
    logger.info("Downloading %s (%s)", pdf.title[:60], pdf.url[:100])
    try:
        resp = await client.get(pdf.url, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError as exc:
        logger.error("Failed to download %s: %s", pdf.url, exc)
        return None
