"""MoR scraper unit tests (mocked API and HTTP)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai_engine.scraper import mor_api, mor_scraper as ms
from ai_engine.scraper.mor_api import MorDiscoveredItem


def test_registry_key_stable() -> None:
    a = ms._registry_key("https://example.com/a.pdf", 100)
    b = ms._registry_key("https://example.com/a.pdf", 100)
    assert a == b
    assert ms._registry_key("https://example.com/a.pdf", 101) != a


@pytest.mark.asyncio
async def test_run_mor_scrape_cycle_inserts_and_skips(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("DOCUMENT_STORAGE_DIR", str(tmp_path))
    item = MorDiscoveredItem(
        pdf_url="https://www.mor.gov.et/static/doc.pdf",
        title="Test Proclamation",
        number=100,
        year=2016,
        status="in force",
        category_name="VAT",
        doc_type="domestic_proclamation",
        external_id="domestic_proclamation:99",
        mor_record_id=99,
    )
    tiny_pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"

    discover_mock = AsyncMock(return_value=[item])
    monkeypatch.setattr(ms, "discover_all_items", discover_mock)

    async def fake_fetch(_client, url: str, **_kwargs):  # noqa: ANN001
        content = tiny_pdf if str(url).endswith(".pdf") else b"{}"
        return httpx.Response(200, content=content, request=httpx.Request("GET", url))

    monkeypatch.setattr(ms, "fetch_with_retry", fake_fetch)

    dup_id = uuid.uuid4()

    class FakeResult:
        def __init__(self, scalar: uuid.UUID | None) -> None:
            self._scalar = scalar

        def scalar_one_or_none(self) -> uuid.UUID | None:
            return self._scalar

    call_count = {"n": 0}

    class FakeSession:
        async def execute(self, stmt):  # noqa: ANN001
            call_count["n"] += 1
            if call_count["n"] == 1:
                return FakeResult(None)
            if call_count["n"] == 2:
                return FakeResult(None)
            if call_count["n"] == 3:
                return FakeResult(None)
            return FakeResult(None)

        def add(self, _obj) -> None:  # noqa: ANN001
            pass

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

        async def refresh(self, doc) -> None:  # noqa: ANN001
            doc.id = dup_id

        async def rollback(self) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):  # noqa: ANN002
            return None

    ingest_mock = AsyncMock()

    with (
        patch.object(ms, "AsyncSessionLocal", lambda: FakeSession()),
        patch.object(ms, "ingest_bytes_for_document", ingest_mock),
    ):
        stats = await ms.run_mor_scrape_cycle(seed_urls=["https://www.mor.gov.et/domestic-law-proclamation"])

    assert stats["discovered"] == 1
    assert stats["inserted"] == 1
    ingest_mock.assert_called_once()

    call_count["n"] = 0

    existing_doc = MagicMock()
    existing_doc.file_hash = __import__("hashlib").sha256(tiny_pdf).hexdigest()
    existing_doc.id = dup_id

    class FakeResultDoc:
        def scalar_one_or_none(self):
            return existing_doc

    class FakeSessionSkip(FakeSession):
        async def execute(self, stmt):  # noqa: ANN001
            call_count["n"] += 1
            if call_count["n"] == 1:
                return FakeResultDoc()
            return FakeResult(None)

    with (
        patch.object(ms, "AsyncSessionLocal", lambda: FakeSessionSkip()),
        patch.object(ms, "ingest_bytes_for_document", ingest_mock),
    ):
        stats2 = await ms.run_mor_scrape_cycle(seed_urls=["https://www.mor.gov.et/domestic-law-proclamation"])

    assert stats2["skipped"] == 1
    assert stats2["inserted"] == 0
