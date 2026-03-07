"""Scraper configuration — target URLs, chunking params, schedule, Redis keys."""

import os

# ---------------------------------------------------------------------------
# MoR source URLs and endpoints (React SPA backed by REST APIs)
# ---------------------------------------------------------------------------
MOR_API_BASE = "https://www.mor.gov.et/api"
MOR_SITE_BASE = "https://www.mor.gov.et"

# Try both host variants in case one path/route is blocked by upstream network
# policy from a given environment.
MOR_API_BASE_CANDIDATES: list[str] = [
    "https://www.mor.gov.et/api",
    "https://mor.gov.et/api",
]

API_ENDPOINTS: list[str] = [
    "/domestic-proclamations",
    "/domestic-regulations",
    "/domestic-directives",
    "/custom-proclamations",
    "/custom-directives",
    "/custom-regulations",
    "/recent-custom-proclamations-regulations",
]

# Fallback HTML pages that historically hosted legal PDFs in a document library.
LEGACY_HTML_SOURCES: list[str] = [
    "/web/mor/proclamations",
    "/web/mor/regulations",
    "/web/mor/directives",
    "/web/mor/forms",
]

# ---------------------------------------------------------------------------
# HTTP client settings
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 60  # seconds per request
HTTP_USER_AGENT = (
    "Mozilla/5.0 (compatible; AwaiqBot/1.0; +https://github.com/awaqi)"
)
# mor.gov.et uses a certificate chain not in the default trust store.
# Set to False to skip verification for this known government endpoint.
VERIFY_SSL: bool = os.getenv("SCRAPER_VERIFY_SSL", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE = 1024       # tokens (whitespace-split words) per chunk
CHUNK_OVERLAP = 100     # overlapping tokens between consecutive chunks

# ---------------------------------------------------------------------------
# Schedule (EAT = UTC+3)
# ---------------------------------------------------------------------------
SCHEDULE_HOURS = [6, 12]        # 06:00 and 12:00 EAT
SCHEDULE_TIMEZONE = "Africa/Addis_Ababa"

# ---------------------------------------------------------------------------
# Redis keys used by the scraper and the API
# ---------------------------------------------------------------------------
REDIS_LOCK_KEY = "scraper:running"
REDIS_LOCK_TTL = 60 * 30           # 30-minute TTL on the distributed lock
REDIS_TRIGGER_KEY = "scraper:trigger"
REDIS_JOB_PREFIX = "scraper:job:"   # scraper:job:{job_id} stores JSON status
REDIS_JOB_TTL = 60 * 60 * 24       # keep job status for 24 hours

# Manual trigger poll interval (seconds)
TRIGGER_POLL_INTERVAL = 10

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/awaqi_db",
)
