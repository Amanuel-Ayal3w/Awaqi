import logging
import os
from contextlib import asynccontextmanager

from ai_engine.web_scraper import WebScraper
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import admin, chat, telegram_link

logger = logging.getLogger(__name__)


async def _safe_scheduled_scrape() -> None:
    try:
        stats = await WebScraper().scan_for_updates()
        logger.info("scheduled_mor_scrape stats=%s", stats)
    except Exception:
        logger.exception("scheduled_mor_scrape_failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler: AsyncIOScheduler | None = None
    enabled = os.getenv("SCRAPER_SCHEDULER_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    if enabled:
        scheduler = AsyncIOScheduler(timezone="Africa/Addis_Ababa")
        scheduler.add_job(
            _safe_scheduled_scrape,
            "cron",
            hour=0,
            minute=0,
            id="mor_daily_scrape",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started: daily MoR scrape at 00:00 Africa/Addis_Ababa")
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Awaqi API", version="1.0.0", lifespan=lifespan)

# Read allowed origins from env so production can lock this down.
# Defaults include both localhost and 127.0.0.1 for local development.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
allowed_origins = list(
    dict.fromkeys([o.strip() for o in _raw_origins.split(",") if o.strip()])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])
app.include_router(telegram_link.router, prefix="/v1/auth/telegram", tags=["telegram"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api"}
