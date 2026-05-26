"""Telegram channel scraper models (MTProto / Telethon)."""

import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class TelegramScrapeRunTrigger(str, PyEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class TelegramScrapeRunStatus(str, PyEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TelegramScraperConfig(Base):
    """Singleton Telegram scraper settings (row id=1)."""

    __tablename__ = "telegram_scraper_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    channel_username: Mapped[str] = mapped_column(String(64), nullable=False, default="morwestaa")
    scrape_since: Mapped[date] = mapped_column(Date, nullable=False)
    max_messages_per_run: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    scheduler_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cron_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cron_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TelegramScrapeRun(Base):
    __tablename__ = "telegram_scrape_runs"

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


class TelegramMessage(Base):
    """One scraped Telegram channel post (text or attachment)."""

    __tablename__ = "telegram_messages"
    content_part: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    __table_args__ = (
        UniqueConstraint(
            "channel_username",
            "message_id",
            "content_part",
            name="uq_telegram_messages_channel_msg_part",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel_username: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scrape_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telegram_scrape_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    skip_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
