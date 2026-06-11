"""Scraper config persistence, run logging, and orchestration."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_engine.scraper.ethiodata_scraper import run_ethiodata_scrape_cycle
from ai_engine.scraper.mor_api import default_seed_urls
from ai_engine.scraper.mor_news_scraper import run_mor_news_scrape_cycle
from ai_engine.scraper.mor_scraper import run_mor_scrape_cycle
from ai_engine.web_scraper import WebScraper
from database.db import AsyncSessionLocal
from database.models.scraper import ScraperConfig, ScraperRun
from sqlalchemy import select

logger = logging.getLogger(__name__)
SCRAPE_SOURCE_MOR_LAWS = "mor_laws"
SCRAPE_SOURCE_ETHIODATA_TAX = "ethiodata_tax"
SCRAPE_SOURCE_MOR_NEWS = "mor_news"
ALL_SCRAPE_SOURCES = {
    SCRAPE_SOURCE_MOR_LAWS,
    SCRAPE_SOURCE_ETHIODATA_TAX,
    SCRAPE_SOURCE_MOR_NEWS,
}


def _merge_stats(*all_stats: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for stats in all_stats:
        for key, value in stats.items():
            merged[key] = merged.get(key, 0) + int(value)
    return merged


@dataclass
class ScraperSettingsView:
    seed_urls: list[str]
    scheduler_enabled: bool
    cron_hour: int
    cron_minute: int
    max_links: int
    storage_dir: str
    api_base_url: str


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").lower()
    return raw in ("1", "true", "yes")


def _default_settings() -> ScraperSettingsView:
    seeds = os.getenv("MOR_SCRAPE_SEED_URLS", ",".join(default_seed_urls())).split(",")
    return ScraperSettingsView(
        seed_urls=[s.strip() for s in seeds if s.strip()],
        scheduler_enabled=_env_bool("SCRAPER_SCHEDULER_ENABLED", True),
        cron_hour=int(os.getenv("SCRAPER_CRON_HOUR", "0")),
        cron_minute=int(os.getenv("SCRAPER_CRON_MINUTE", "0")),
        max_links=int(os.getenv("MOR_SCRAPE_MAX_LINKS", "30")),
        storage_dir=os.getenv("DOCUMENT_STORAGE_DIR", "data/documents"),
        api_base_url=os.getenv("MOR_API_BASE_URL", "https://www.mor.gov.et/api"),
    )


async def ensure_scraper_config_row() -> ScraperConfig:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScraperConfig).where(ScraperConfig.id == 1))
        row = result.scalar_one_or_none()
        if row is not None:
            return row
        defaults = _default_settings()
        row = ScraperConfig(
            id=1,
            seed_urls=",".join(defaults.seed_urls),
            scheduler_enabled=defaults.scheduler_enabled,
            cron_hour=defaults.cron_hour,
            cron_minute=defaults.cron_minute,
            max_links=defaults.max_links,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


async def get_scraper_settings() -> ScraperSettingsView:
    defaults = _default_settings()
    try:
        row = await ensure_scraper_config_row()
    except Exception:
        logger.exception("scraper_config_load_failed_using_env")
        return defaults

    seeds = [s.strip() for s in row.seed_urls.split(",") if s.strip()]
    return ScraperSettingsView(
        seed_urls=seeds or defaults.seed_urls,
        scheduler_enabled=bool(row.scheduler_enabled),
        cron_hour=int(row.cron_hour),
        cron_minute=int(row.cron_minute),
        max_links=int(row.max_links),
        storage_dir=defaults.storage_dir,
        api_base_url=defaults.api_base_url,
    )


async def update_scraper_settings(
    *,
    seed_urls: list[str] | None = None,
    scheduler_enabled: bool | None = None,
    cron_hour: int | None = None,
    cron_minute: int | None = None,
    max_links: int | None = None,
) -> ScraperSettingsView:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScraperConfig).where(ScraperConfig.id == 1))
        row = result.scalar_one_or_none()
        if row is None:
            row = await ensure_scraper_config_row()
            result = await db.execute(select(ScraperConfig).where(ScraperConfig.id == 1))
            row = result.scalar_one()

        if seed_urls is not None:
            row.seed_urls = ",".join(seed_urls)
        if scheduler_enabled is not None:
            row.scheduler_enabled = scheduler_enabled
        if cron_hour is not None:
            row.cron_hour = cron_hour
        if cron_minute is not None:
            row.cron_minute = cron_minute
        if max_links is not None:
            row.max_links = max_links
        row.updated_at = datetime.now(timezone.utc)
        await db.commit()

    return await get_scraper_settings()


async def execute_scrape_run(trigger: str) -> dict[str, int]:
    """Run one scrape cycle with DB config and record history."""
    settings = await get_scraper_settings()
    run_id = None
    async with AsyncSessionLocal() as db:
        run = ScraperRun(
            trigger=trigger,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    stats: dict[str, int] = {
        "discovered": 0,
        "inserted": 0,
        "skipped": 0,
        "errors": 0,
    }
    error_message: str | None = None
    try:
        mor_stats: dict[str, int] = {}
        ethiodata_stats: dict[str, int] = {}
        mor_news_stats: dict[str, int] = {}
        mor_stats = await WebScraper().scan_for_updates(
            seed_urls=settings.seed_urls,
            max_links=settings.max_links,
        )
        ethiodata_stats = await run_ethiodata_scrape_cycle(max_articles=settings.max_links)
        mor_news_stats = await run_mor_news_scrape_cycle(max_links=settings.max_links)
        stats = _merge_stats(mor_stats, ethiodata_stats, mor_news_stats)
        status = "success"
    except Exception as e:
        logger.exception("scrape_run_failed trigger=%s", trigger)
        status = "failed"
        error_message = str(e)[:2000]
        stats["errors"] = stats.get("errors", 0) + 1

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScraperRun).where(ScraperRun.id == run_id))
        run = result.scalar_one()
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        run.stats = stats
        run.error_message = error_message
        await db.commit()

    return stats


async def _execute_scrape_run_with_progress(
    trigger: str,
    seed_urls: list[str] | None,
    max_links: int | None,
    on_progress: Callable[[int, int, str], None] | None,
    sources: list[str] | None = None,
) -> dict[str, int]:
    """Low-level: run cycle with optional progress callback + persist run record."""
    settings = await get_scraper_settings()
    run_id = None
    async with AsyncSessionLocal() as db:
        run = ScraperRun(
            trigger=trigger,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    effective_seeds = seed_urls if seed_urls is not None else settings.seed_urls
    effective_max = max_links if max_links is not None else settings.max_links

    selected_sources = (
        set(sources) & ALL_SCRAPE_SOURCES if sources is not None else set(ALL_SCRAPE_SOURCES)
    )
    if not selected_sources:
        raise ValueError("At least one scrape source must be selected")

    stats: dict[str, int] = {"discovered": 0, "inserted": 0, "skipped": 0, "errors": 0}
    error_message: str | None = None
    try:
        selected_order = [
            s
            for s in (
                SCRAPE_SOURCE_MOR_LAWS,
                SCRAPE_SOURCE_ETHIODATA_TAX,
                SCRAPE_SOURCE_MOR_NEWS,
            )
            if s in selected_sources
        ]
        phase_span = 100 // max(1, len(selected_order))
        phase_offsets: dict[str, int] = {
            source: idx * phase_span for idx, source in enumerate(selected_order)
        }

        def _phase_progress(source: str, cur: int, total: int, step: str) -> None:
            if on_progress is None:
                return
            offset = phase_offsets[source]
            local_pct = 0 if total <= 0 else int((cur / total) * phase_span)
            on_progress(min(99, offset + local_pct), 100, step)

        mor_stats: dict[str, int] = {}
        ethiodata_stats: dict[str, int] = {}
        mor_news_stats: dict[str, int] = {}

        if SCRAPE_SOURCE_MOR_LAWS in selected_sources:
            mor_stats = await run_mor_scrape_cycle(
                seed_urls=effective_seeds,
                max_links=effective_max,
                on_progress=(
                    (lambda cur, total, step: _phase_progress(
                        SCRAPE_SOURCE_MOR_LAWS,
                        cur,
                        total,
                        f"MoR laws: {step}",
                    ))
                    if on_progress is not None
                    else None
                ),
            )
        if SCRAPE_SOURCE_ETHIODATA_TAX in selected_sources:
            ethiodata_stats = await run_ethiodata_scrape_cycle(
                max_articles=effective_max,
                on_progress=(
                    (lambda cur, total, step: _phase_progress(
                        SCRAPE_SOURCE_ETHIODATA_TAX,
                        cur,
                        total,
                        f"EthioData tax: {step}",
                    ))
                    if on_progress is not None
                    else None
                ),
            )
        if SCRAPE_SOURCE_MOR_NEWS in selected_sources:
            mor_news_stats = await run_mor_news_scrape_cycle(
                max_links=effective_max,
                on_progress=(
                    (lambda cur, total, step: _phase_progress(
                        SCRAPE_SOURCE_MOR_NEWS,
                        cur,
                        total,
                        f"MoR news: {step}",
                    ))
                    if on_progress is not None
                    else None
                ),
            )
        stats = _merge_stats(mor_stats, ethiodata_stats, mor_news_stats)
        run_status = "success"
    except Exception as e:
        logger.exception("scrape_run_failed trigger=%s", trigger)
        run_status = "failed"
        error_message = str(e)[:2000]
        stats["errors"] = stats.get("errors", 0) + 1

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScraperRun).where(ScraperRun.id == run_id))
        run = result.scalar_one()
        run.status = run_status
        run.finished_at = datetime.now(timezone.utc)
        run.stats = stats
        run.error_message = error_message
        await db.commit()

    return stats


async def get_last_scraper_run() -> ScraperRun | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()


async def list_scraper_runs(limit: int = 20) -> list[ScraperRun]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
