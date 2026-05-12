"""MoR scraper unit tests (mocked HTTP and DB)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai_engine.scraper import mor_scraper as ms


def test_extract_pdf_links_basic() -> None:
    html = '<html><body><a href="/files/a.pdf">A</a><a href="https://other.example/x.pdf">B</a></body></html>'
    found = ms._extract_pdf_links(html, "https://www.mor.gov.et/web/mor/proclamations")
    assert "https://www.mor.gov.et/files/a.pdf" in found
    assert "https://other.example/x.pdf" in found


def test_extract_same_site_html_links() -> None:
    html = (
        '<html><body>'
        '<a href="/web/mor/directives">Directives</a>'
        '<a href="https://evil.example/phish">Bad</a>'
        '<a href="mailto:x@y.com">m</a>'
        "</body></html>"
    )
    allowed = ms._allowed_hosts_from_seeds(["https://www.mor.gov.et/"])
    links = ms._extract_same_site_html_links(html, "https://www.mor.gov.et/", allowed)
    assert any("/web/mor/directives" in u for u in links)
    assert all("evil.example" not in u for u in links)


def test_visit_key_normalizes() -> None:
    a = ms._visit_key("HTTPS://WWW.Mor.Gov.Et/web/X?y=1#frag")
    b = ms._visit_key("https://www.mor.gov.et/web/X?y=1")
    assert a == b


@pytest.mark.asyncio
async def test_discover_pdf_urls_respects_max_links(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ms, "DEFAULT_SEEDS", ["https://www.mor.gov.et/seed"])
    monkeypatch.setattr(ms, "MAX_DEPTH", 0)
    monkeypatch.setattr(ms, "MAX_PAGES_PER_RUN", 5)
    monkeypatch.setattr(ms, "MAX_LINKS_PER_RUN", 2)

    html = '<html><a href="/a.pdf">a</a><a href="/b.pdf">b</a><a href="/c.pdf">c</a></html>'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html.encode(), request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        urls = await ms._discover_pdf_urls(client)
    assert len(urls) <= 2


@pytest.mark.asyncio
async def test_run_mor_scrape_cycle_skips_duplicate_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ms, "DEFAULT_SEEDS", ["https://www.mor.gov.et/one"])
    monkeypatch.setattr(ms, "MAX_DEPTH", 0)
    monkeypatch.setattr(ms, "MAX_PAGES_PER_RUN", 3)
    monkeypatch.setattr(ms, "MAX_LINKS_PER_RUN", 5)

    pdf_url = "https://www.mor.gov.et/static/doc.pdf"
    tiny_pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"

    html = f'<html><a href="{pdf_url}">d</a></html>'

    def transport_handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.mor.gov.et" and request.url.path.endswith(".pdf"):
            return httpx.Response(200, content=tiny_pdf, request=request)
        return httpx.Response(200, content=html.encode(), request=request)

    dup_id = uuid.uuid4()

    class FakeResult:
        def __init__(self, scalar: uuid.UUID | None) -> None:
            self._scalar = scalar

        def scalar_one_or_none(self) -> uuid.UUID | None:
            return self._scalar

    class FakeSession:
        def __init__(self) -> None:
            self.registry_calls = 0

        async def execute(self, stmt: object) -> FakeResult:
            self.registry_calls += 1
            if self.registry_calls == 1:
                return FakeResult(dup_id)
            return FakeResult(None)

        async def commit(self) -> None:
            pass

        async def refresh(self, doc: object) -> None:
            pass

        async def rollback(self) -> None:
            pass

        def add(self, doc: object) -> None:
            pass

    fake = FakeSession()

    class FakeCM:
        async def __aenter__(self) -> FakeSession:
            return fake

        async def __aexit__(self, *a: object) -> None:
            pass

    mock_local = MagicMock(return_value=FakeCM())

    ingest_mock = AsyncMock()

    real_async_client = httpx.AsyncClient

    def custom_client(**kw: object) -> httpx.AsyncClient:
        return real_async_client(transport=httpx.MockTransport(transport_handler))

    with (
        patch.object(ms, "AsyncSessionLocal", mock_local),
        patch.object(ms, "ingest_bytes_for_document", ingest_mock),
        patch.object(ms.httpx, "AsyncClient", custom_client),
    ):
        stats = await ms.run_mor_scrape_cycle()

    assert stats["skipped"] >= 1
    assert stats["inserted"] == 0
    ingest_mock.assert_not_called()
