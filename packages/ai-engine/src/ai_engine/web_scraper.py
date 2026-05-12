"""
SDS-aligned Web acquisition façade (Phase A1).

``WebScraper.scan_for_updates`` is the single entrypoint used by the scheduled job
and ``POST /v1/admin/scrape`` (AWA-5 / AWA-11).
"""

from __future__ import annotations

from ai_engine.scraper.mor_scraper import run_mor_scrape_cycle


class WebScraper:
    """MoR discovery + download + registry dedup + ingest (implementation in ``scraper/``)."""

    async def scan_for_updates(self) -> dict[str, int]:
        return await run_mor_scrape_cycle()
