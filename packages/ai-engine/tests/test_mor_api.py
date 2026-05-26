"""MoR API client unit tests."""

from __future__ import annotations

import httpx
import pytest
from ai_engine.scraper import mor_api as api


def test_families_from_seed_urls_maps_six_routes() -> None:
    seeds = api.default_seed_urls()
    families = api.families_from_seed_urls(seeds)
    assert len(families) == 6
    doc_types = {f.doc_type for f in families}
    assert "domestic_proclamation" in doc_types
    assert "custom_regulation" in doc_types


def test_parse_item_skips_deleted_and_missing_pdf() -> None:
    assert api._parse_item({"id": 1, "deleted": True, "pdfFile": "http://x/a.pdf"}, doc_type="t", category_name=None) is None
    assert api._parse_item({"id": 1, "title": "T"}, doc_type="t", category_name=None) is None


def test_parse_item_ok() -> None:
    item = api._parse_item(
        {
            "id": 42,
            "title": "Test law",
            "pdfFile": "https://www.mor.gov.et/foo.pdf",
            "number": 133,
            "year": 1999,
            "status": "in force",
        },
        doc_type="domestic_regulation",
        category_name="VAT",
    )
    assert item is not None
    assert item.external_id == "domestic_regulation:42"
    assert item.pdf_url.endswith(".pdf")


@pytest.mark.asyncio
async def test_discover_family_items_mocked() -> None:
    categories = [{"id": 1, "name": "Cat", "engName": "Category", "deleted": False}]
    items = [
        {
            "id": 10,
            "title": "Doc",
            "pdfFile": "https://www.mor.gov.et/a.pdf",
            "number": 1,
            "year": 2020,
            "status": "in force",
            "deleted": False,
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/domestic-proclamation-categories"):
            return httpx.Response(200, json=categories, request=request)
        if path.endswith("/domestic-proclamation-by-category/1"):
            return httpx.Response(200, json=items, request=request)
        return httpx.Response(404, request=request)

    family = api.MorApiFamily(
        doc_type="domestic_proclamation",
        categories_path="domestic-proclamation-categories",
        items_path_prefix="domestic-proclamation-by-category",
    )
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=api.MOR_API_BASE) as client:
        discovered = await api.discover_family_items(client, family)
    assert len(discovered) == 1
    assert discovered[0].external_id == "domestic_proclamation:10"
