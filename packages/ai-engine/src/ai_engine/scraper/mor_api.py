"""
MoR REST API client for law document discovery (SPA renders via JS; PDFs come from API).

Public API base: ``https://www.mor.gov.et/api`` (see MoR frontend bundle).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from ai_engine.scraper.http_retry import fetch_with_retry

logger = logging.getLogger(__name__)

MOR_API_BASE = os.getenv("MOR_API_BASE_URL", "https://www.mor.gov.et/api").rstrip("/")

# Frontend route path (last segment) → API family
_ROUTE_FAMILIES: dict[str, tuple[str, str, str]] = {
    "custom-law-proclamation": (
        "custom_proclamation",
        "custom-proclamation-categories",
        "custom-proclamation-by-category",
    ),
    "custome-law-regulation": (
        "custom_regulation",
        "custom-regulation-categories",
        "custom-regulation-by-category",
    ),
    "custome-law-directive": (
        "custom_directive",
        "custom-directive-categories",
        "custom-directive-by-category",
    ),
    "domestic-law-proclamation": (
        "domestic_proclamation",
        "domestic-proclamation-categories",
        "domestic-proclamation-by-category",
    ),
    "domestic-law-regulation": (
        "domestic_regulation",
        "domestic-regulation-categories",
        "domestic-regulation-by-category",
    ),
    "domestic-law-directive": (
        "domestic_directive",
        "domestic-directive-categories",
        "domestic-directive-by-category",
    ),
}

DEFAULT_SEED_PATHS = list(_ROUTE_FAMILIES.keys())


@dataclass(frozen=True)
class MorApiFamily:
    doc_type: str
    categories_path: str
    items_path_prefix: str


@dataclass(frozen=True)
class MorDiscoveredItem:
    pdf_url: str
    title: str
    number: int | None
    year: int | None
    status: str | None
    category_name: str | None
    doc_type: str
    external_id: str
    mor_record_id: int


def _all_families() -> list[MorApiFamily]:
    return [
        MorApiFamily(
            doc_type=doc_type,
            categories_path=cat_path,
            items_path_prefix=items_prefix,
        )
        for doc_type, cat_path, items_prefix in _ROUTE_FAMILIES.values()
    ]


def families_from_seed_urls(seed_urls: list[str]) -> list[MorApiFamily]:
    """Map seed page URLs to unique MoR API families."""
    seen: set[str] = set()
    out: list[MorApiFamily] = []
    for raw in seed_urls:
        url = raw.strip()
        if not url:
            continue
        path = urlparse(url).path.rstrip("/")
        segment = path.rsplit("/", 1)[-1] if path else ""
        spec = _ROUTE_FAMILIES.get(segment)
        if spec is None:
            logger.warning("mor_api_unknown_seed_segment segment=%s url=%s", segment, url)
            continue
        doc_type, cat_path, items_prefix = spec
        if doc_type in seen:
            continue
        seen.add(doc_type)
        out.append(
            MorApiFamily(
                doc_type=doc_type,
                categories_path=cat_path,
                items_path_prefix=items_prefix,
            )
        )
    if not out:
        logger.warning(
            "mor_api_no_families_mapped_from_seeds; using all %d API families",
            len(_ROUTE_FAMILIES),
        )
        return _all_families()
    return out


def default_seed_urls() -> list[str]:
    base = "https://www.mor.gov.et"
    return [f"{base}/{path}" for path in DEFAULT_SEED_PATHS]


def _category_name(cat: dict) -> str | None:
    eng = cat.get("engName") or cat.get("eng_name")
    if eng:
        return str(eng)
    name = cat.get("name")
    return str(name) if name else None


def _item_category_name(item: dict) -> str | None:
    for key in (
        "ProclamationCategory",
        "RegulationCategory",
        "DirectiveCategory",
        "CustomProclamationCategory",
        "CustomRegulationCategory",
        "CustomDirectiveCategory",
    ):
        nested = item.get(key)
        if isinstance(nested, dict):
            return _category_name(nested)
    return None


def _parse_item(item: dict, *, doc_type: str, category_name: str | None) -> MorDiscoveredItem | None:
    if item.get("deleted") is True:
        return None
    pdf = (item.get("pdfFile") or item.get("pdf_file") or "").strip()
    if not pdf:
        return None
    record_id = item.get("id")
    if record_id is None:
        return None
    title = (item.get("title") or "Untitled").strip()[:512]
    number = item.get("number")
    year = item.get("year")
    status = item.get("status")
    return MorDiscoveredItem(
        pdf_url=pdf,
        title=title,
        number=int(number) if number is not None else None,
        year=int(year) if year is not None else None,
        status=str(status) if status is not None else None,
        category_name=category_name or _item_category_name(item),
        doc_type=doc_type,
        external_id=f"{doc_type}:{record_id}",
        mor_record_id=int(record_id),
    )


async def _fetch_json(client: httpx.AsyncClient, path: str) -> list | dict:
    url = f"{MOR_API_BASE}/{path.lstrip('/')}"
    resp = await fetch_with_retry(client, url)
    return resp.json()


async def discover_family_items(
    client: httpx.AsyncClient,
    family: MorApiFamily,
) -> list[MorDiscoveredItem]:
    """List all PDF-backed items for one API family (categories → items)."""
    discovered: list[MorDiscoveredItem] = []
    try:
        categories_raw = await _fetch_json(client, family.categories_path)
    except Exception:
        logger.exception(
            "mor_api_categories_failed family=%s path=%s",
            family.doc_type,
            family.categories_path,
        )
        return discovered

    if not isinstance(categories_raw, list):
        logger.warning(
            "mor_api_categories_unexpected family=%s type=%s",
            family.doc_type,
            type(categories_raw).__name__,
        )
        return discovered

    for cat in categories_raw:
        if not isinstance(cat, dict):
            continue
        if cat.get("deleted") is True:
            continue
        cat_id = cat.get("id")
        if cat_id is None:
            continue
        cat_name = _category_name(cat)
        items_path = f"{family.items_path_prefix}/{cat_id}"
        try:
            items_raw = await _fetch_json(client, items_path)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(
                    "mor_api_items_empty family=%s category_id=%s",
                    family.doc_type,
                    cat_id,
                )
            else:
                logger.warning(
                    "mor_api_items_failed family=%s category_id=%s status=%s",
                    family.doc_type,
                    cat_id,
                    e.response.status_code,
                )
            continue
        except Exception as e:
            logger.warning(
                "mor_api_items_failed family=%s category_id=%s err=%s",
                family.doc_type,
                cat_id,
                e,
            )
            continue
        if not isinstance(items_raw, list):
            continue
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            parsed = _parse_item(item, doc_type=family.doc_type, category_name=cat_name)
            if parsed is not None:
                discovered.append(parsed)

    return discovered


async def discover_all_items(
    client: httpx.AsyncClient,
    seed_urls: list[str],
) -> list[MorDiscoveredItem]:
    """Discover PDF items across all API families implied by seed URLs."""
    families = families_from_seed_urls(seed_urls)

    all_items: list[MorDiscoveredItem] = []
    seen_external: set[str] = set()
    for family in families:
        items = await discover_family_items(client, family)
        for item in items:
            if item.external_id in seen_external:
                continue
            seen_external.add(item.external_id)
            all_items.append(item)
    return all_items
