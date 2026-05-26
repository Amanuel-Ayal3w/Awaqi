import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import admin, chat, telegram_link
from apps.api.scraper_scheduler import apply_scheduler_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.scraper_scheduler = None
    try:
        await apply_scheduler_config(app)
    except Exception:
        logger.exception("scraper_scheduler_startup_failed")
    yield
    scheduler = getattr(app.state, "scraper_scheduler", None)
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Awaqi API", version="1.0.0", lifespan=lifespan)

# Read allowed origins from env so production can lock this down.
# Defaults include both localhost and 127.0.0.1 for local development.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3100,http://127.0.0.1:3100",
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
