"""MoR and other ingestion scrapers."""

from ai_engine.scraper.mor_api import MorDiscoveredItem, default_seed_urls, discover_all_items
from ai_engine.scraper.ethiodata_scraper import run_ethiodata_scrape_cycle
from ai_engine.scraper.mor_news_scraper import run_mor_news_scrape_cycle
from ai_engine.scraper.mor_scraper import run_mor_scrape_cycle

__all__ = [
    "MorDiscoveredItem",
    "default_seed_urls",
    "discover_all_items",
    "run_mor_scrape_cycle",
    "run_ethiodata_scrape_cycle",
    "run_mor_news_scrape_cycle",
]
