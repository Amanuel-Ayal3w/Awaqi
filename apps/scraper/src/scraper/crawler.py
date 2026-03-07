"""Discover and download PDF files from mor.gov.et sources."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from scraper.config import (
    API_ENDPOINTS,
    HTTP_TIMEOUT,
    HTTP_USER_AGENT,
    LEGACY_HTML_SOURCES,
    MOR_API_BASE,
    MOR_API_BASE_CANDIDATES,
    MOR_SITE_BASE,
    VERIFY_SSL,
)

logger = logging.getLogger(__name__)

_DISCOVERY_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=min(float(HTTP_TIMEOUT), 20.0),
    write=10.0,
    pool=10.0,
)
_TRANSPORT_ERRORS = {"ReadTimeout", "ConnectTimeout", "ConnectError", "PoolTimeout"}
_PDF_URL_KEYS = (
    "pdfFile",
    "pdf_file",
    "pdfUrl",
    "pdf_url",
    "documentUrl",
    "document_url",
    "fileUrl",
    "file_url",
    "url",
)
_TITLE_KEYS = ("title", "name", "documentTitle", "description")
_PDF_LINK_RE = re.compile(
    r"""(?P<link>https?://[^\s"'<>]+\.pdf(?:\?[^\s"'<>]*)?|/[^\s"'<>]+\.pdf(?:\?[^\s"'<>]*)?)""",
    flags=re.IGNORECASE,
)
_LEGACY_VIEW_FILE_RE = re.compile(
    r"""(?P<link>/web/mor/[^\s"'<>]*/document_library/[^\s"'<>]*/view_file/\d+)""",
    flags=re.IGNORECASE,
)
_BUNDLE_API_PATH_RE = re.compile(
    r"""["'](?P<path>/(?:domestic|custom|recent)[a-z0-9\-_/\$]*)["']""",
    flags=re.IGNORECASE,
)

@dataclass
class PdfInfo:
    """Metadata for a discovered PDF before downloading."""

    url: str
    title: str
    source_endpoint: str


def _normalize_url(raw_url: str) -> str | None:
    url = (raw_url or "").strip()
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return urljoin(MOR_SITE_BASE, url)
    if re.match(r"^https?://", url, flags=re.IGNORECASE):
        return url
    return urljoin(f"{MOR_SITE_BASE}/", url.lstrip("./"))


def _looks_like_pdf_candidate(url: str) -> bool:
    lowered = url.lower()
    if ".pdf" in lowered:
        return True
    return "/view_file/" in lowered or "/document_library/" in lowered


def _title_from_url(url: str) -> str:
    path = urlparse(url).path
    tail = path.rstrip("/").split("/")[-1]
    return tail or "Untitled"


def _extract_pdf_url(item: dict) -> str | None:
    for key in _PDF_URL_KEYS:
        value = item.get(key)
        if isinstance(value, str):
            normalized = _normalize_url(value)
            if normalized and (_looks_like_pdf_candidate(normalized) or "pdf" in key.lower()):
                return normalized
    for nested in item.values():
        if isinstance(nested, dict):
            nested_url = _extract_pdf_url(nested)
            if nested_url:
                return nested_url
    return None


def _extract_from_payload(payload: object, source_endpoint: str) -> list[PdfInfo]:
    if isinstance(payload, list):
        records: list[object] = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            records = payload["data"]
        elif isinstance(payload.get("results"), list):
            records = payload["results"]
        elif isinstance(payload.get("items"), list):
            records = payload["items"]
        else:
            records = [payload]
    else:
        return []

    results: list[PdfInfo] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        pdf_url = _extract_pdf_url(record)
        if not pdf_url:
            continue
        title = "Untitled"
        for key in _TITLE_KEYS:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                title = value.strip()
                break
        if title == "Untitled":
            title = _title_from_url(pdf_url)
        results.append(PdfInfo(url=pdf_url, title=title, source_endpoint=source_endpoint))
    return results


async def _fetch_endpoint(
    client: httpx.AsyncClient,
    api_base: str,
    endpoint: str,
) -> tuple[list[PdfInfo], str | None]:
    """Fetch one API endpoint and return extracted PDF entries + error type."""
    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    logger.info("Fetching %s", url)
    started = time.perf_counter()
    try:
        resp = await client.get(url, follow_redirects=True, timeout=_DISCOVERY_TIMEOUT)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "Failed to fetch %s (%s after %dms): %s",
            endpoint,
            type(exc).__name__,
            elapsed_ms,
            exc,
        )
        return [], type(exc).__name__
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning("Failed to parse payload from %s: %s", url, exc)
        return [], type(exc).__name__

    results = _extract_from_payload(data, source_endpoint=endpoint)
    logger.info(
        "Found %d PDF candidate(s) from %s (base=%s)",
        len(results),
        endpoint,
        api_base,
    )
    return results, None


async def _extract_dynamic_endpoints(client: httpx.AsyncClient) -> list[str]:
    """Read the frontend bundle and extract candidate API paths."""
    discovered: set[str] = set()
    try:
        home = await client.get(
            MOR_SITE_BASE, follow_redirects=True, timeout=_DISCOVERY_TIMEOUT
        )
        home.raise_for_status()
    except Exception as exc:
        logger.warning("Skipping bundle endpoint discovery: %s", exc)
        return []

    soup = BeautifulSoup(home.text, "html.parser")
    script_sources = [
        _normalize_url(tag.get("src", ""))
        for tag in soup.find_all("script")
        if tag.get("src")
    ]

    for script_url in script_sources[:20]:
        if not script_url:
            continue
        try:
            script_resp = await client.get(
                script_url, follow_redirects=True, timeout=_DISCOVERY_TIMEOUT
            )
            script_resp.raise_for_status()
        except Exception:
            continue
        for match in _BUNDLE_API_PATH_RE.finditer(script_resp.text):
            path = match.group("path").replace("${", "").replace("}", "")
            if not path.startswith("/"):
                continue
            path = "/" + path.strip("/").split("/${")[0]
            if "proclamation" in path or "regulation" in path or "directive" in path:
                discovered.add(path)

    dynamic = sorted(
        endpoint for endpoint in discovered if endpoint not in set(API_ENDPOINTS)
    )
    if dynamic:
        logger.info("Discovered %d dynamic API endpoint(s) from MoR bundle", len(dynamic))
    return dynamic


async def _discover_from_html_sources(client: httpx.AsyncClient) -> list[PdfInfo]:
    """Fallback strategy: parse known MoR HTML pages for PDF links."""
    source_paths = list(LEGACY_HTML_SOURCES) + [
        "/proclamations",
        "/regulations",
        "/directives",
        "/forms",
    ]
    seen_links: set[str] = set()
    results: list[PdfInfo] = []

    for path in source_paths:
        page_url = _normalize_url(path)
        if not page_url:
            continue
        try:
            resp = await client.get(
                page_url, follow_redirects=True, timeout=_DISCOVERY_TIMEOUT
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("HTML fallback fetch failed for %s: %s", page_url, exc)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        linked_urls: set[str] = set()

        for tag in soup.find_all(["a", "iframe", "embed", "object"]):
            for attr in ("href", "src", "data"):
                value = tag.get(attr)
                if not isinstance(value, str):
                    continue
                normalized = _normalize_url(value)
                if normalized and _looks_like_pdf_candidate(normalized):
                    linked_urls.add(normalized)

        for match in _PDF_LINK_RE.finditer(resp.text):
            normalized = _normalize_url(match.group("link"))
            if normalized:
                linked_urls.add(normalized)

        for match in _LEGACY_VIEW_FILE_RE.finditer(resp.text):
            normalized = _normalize_url(match.group("link"))
            if normalized:
                linked_urls.add(normalized)

        for candidate in linked_urls:
            if candidate in seen_links:
                continue
            seen_links.add(candidate)
            results.append(
                PdfInfo(
                    url=candidate,
                    title=_title_from_url(candidate),
                    source_endpoint=f"html:{path}",
                )
            )

    return results


async def _collect_api_results(
    client: httpx.AsyncClient,
    endpoints: list[str],
) -> list[PdfInfo]:
    collected: list[PdfInfo] = []
    seen_urls: set[str] = set()

    api_bases = [MOR_API_BASE]
    for candidate in MOR_API_BASE_CANDIDATES:
        if candidate not in api_bases:
            api_bases.append(candidate)

    for api_base in api_bases:
        consecutive_transport_errors = 0
        saw_success = False
        for endpoint in endpoints:
            pdfs, error_type = await _fetch_endpoint(client, api_base, endpoint)

            if error_type in _TRANSPORT_ERRORS:
                consecutive_transport_errors += 1
            else:
                consecutive_transport_errors = 0
            if error_type is None:
                saw_success = True

            for pdf in pdfs:
                if pdf.url in seen_urls:
                    continue
                seen_urls.add(pdf.url)
                collected.append(pdf)

            if consecutive_transport_errors >= 2 and not saw_success:
                logger.warning(
                    "Skipping remaining endpoints for %s after repeated transport errors",
                    api_base,
                )
                break

    return collected


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

    try:
        all_pdfs = await _collect_api_results(client, API_ENDPOINTS)

        if not all_pdfs:
            dynamic_endpoints = await _extract_dynamic_endpoints(client)
            if dynamic_endpoints:
                logger.info(
                    "Primary API discovery returned 0 PDFs; retrying with %d dynamic endpoint(s)",
                    len(dynamic_endpoints),
                )
                all_pdfs = await _collect_api_results(client, dynamic_endpoints)

        if not all_pdfs:
            logger.info("API discovery returned 0 PDFs; trying HTML fallback sources")
            all_pdfs = await _discover_from_html_sources(client)
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
        content_type = resp.headers.get("content-type", "").lower()
        payload = resp.content
        if not payload:
            logger.warning("Downloaded empty body from %s", pdf.url)
            return None
        if "pdf" not in content_type and not payload.startswith(b"%PDF-"):
            logger.warning(
                "Skipping non-PDF response from %s (status=%d content-type=%s)",
                pdf.url,
                resp.status_code,
                content_type or "unknown",
            )
            return None
        return payload
    except httpx.HTTPError as exc:
        logger.error("Failed to download %s: %s", pdf.url, exc)
        return None
