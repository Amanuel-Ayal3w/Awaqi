"""Notification system ORM models.

- NotificationConfig: singleton (id=1) storing scheduler settings, recipients,
  and the watermark timestamp used to detect newly-indexed documents.
- NotificationLog: one row per notification attempt (email or SMS).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class NotificationConfig(Base):
    """Singleton notification settings row (id = 1)."""

    __tablename__ = "notification_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    scheduler_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Interval between checks (1 = every hour, 6 = every 6 hours, etc.)
    interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Comma-separated list of email addresses to notify
    email_recipients: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Comma-separated list of phone numbers (with country code, e.g. 25191...)
    sms_recipients: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Minimum LLM relevance score (0.0–1.0) required to send a notification
    min_relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.7
    )

    # Watermark: only documents indexed after this timestamp are considered
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class NotificationLog(Base):
    """One row per notification send attempt (email or SMS)."""

    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Which document triggered this notification (nullable — could be a batch)
    doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    doc_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(8), nullable=False
    )  # "email" or "sms"
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="sent"
    )  # "sent" | "failed"
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(
        String(16), nullable=False, default="scheduled"
    )  # "scheduled" | "manual"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog id={self.id} channel={self.channel} "
            f"recipient={self.recipient!r} status={self.status}>"
        )


class Announcement(Base):
    """A significant public announcement surfaced by the LLM relevance check.

    One row per relevant document — the in-app notification feed for the user portal.
    """

    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    doc_title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    trigger: Mapped[str] = mapped_column(
        String(16), nullable=False, default="scheduled"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Announcement id={self.id} title={self.doc_title!r}>"
