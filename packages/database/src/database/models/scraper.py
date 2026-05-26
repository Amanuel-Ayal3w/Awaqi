"""Scraper configuration and run history (AWA-5 / AWA-11)."""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class ScrapeRunTrigger(str, PyEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class ScrapeRunStatus(str, PyEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScraperConfig(Base):
    """Singleton scraper settings (row id=1)."""

    __tablename__ = "scraper_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    seed_urls: Mapped[str] = mapped_column(Text, nullable=False)
    scheduler_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cron_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cron_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_links: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
