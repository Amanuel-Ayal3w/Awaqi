"""Proactive notification service.

Responsibilities:
- Persist / read ``NotificationConfig`` (singleton row id=1).
- Query documents indexed after the watermark timestamp.
- Use an LLM to assess whether each new document is a noteworthy announcement.
- Send email (Mailtrap SMTP) and SMS (GeezSMS REST API) to subscribed recipients.
- Write a ``NotificationLog`` row for every send attempt.
- Advance the watermark so the same documents are not re-evaluated.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from textwrap import dedent
from typing import Any

import httpx
from database.db import AsyncSessionLocal
from database.models.document import Document, DocumentChunk, DocumentStatus
from database.models.notification import (
    Announcement,
    NotificationConfig,
    NotificationLog,
)
from sqlalchemy import select

logger = logging.getLogger(__name__)

# ─── Environment helpers ──────────────────────────────────────────────────────

MAILTRAP_HOST = os.getenv("MAILTRAP_HOST", "sandbox.smtp.mailtrap.io")
MAILTRAP_PORT = int(os.getenv("MAILTRAP_PORT", "587"))
MAILTRAP_USERNAME = os.getenv("MAILTRAP_USERNAME", "")
MAILTRAP_PASSWORD = os.getenv("MAILTRAP_PASSWORD", "")
MAILTRAP_FROM_EMAIL = os.getenv("MAILTRAP_FROM_EMAIL", "noreply@awaqi.et")
MAILTRAP_FROM_NAME = os.getenv("MAILTRAP_FROM_NAME", "Awaqi – Ethiopian Tax Advisory")

GEEZSMS_API_URL = "https://api.geezsms.com/api/v1/sms/send"
GEEZSMS_TOKEN = os.getenv("GEEZSMS_TOKEN", "")
GEEZSMS_SHORTCODE_ID = os.getenv("GEEZSMS_SHORTCODE_ID", "")

NOTIFICATION_FROM_NAME = os.getenv("NOTIFICATION_FROM_NAME", "Awaqi Tax Advisory")

# Number of document chunks to feed the LLM for relevance evaluation
_EVAL_CHUNKS = 2
# Max characters of chunk content sent to the LLM
_MAX_CONTENT_CHARS = 3000


# ─── Settings dataclass ───────────────────────────────────────────────────────


@dataclass
class NotificationSettingsView:
    scheduler_enabled: bool
    interval_hours: int
    email_recipients: list[str]
    sms_recipients: list[str]
    min_relevance_score: float
    last_checked_at: datetime | None


# ─── Config persistence ───────────────────────────────────────────────────────


async def ensure_notification_config_row() -> NotificationConfig:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NotificationConfig).where(NotificationConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return row
        row = NotificationConfig(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


async def get_notification_settings() -> NotificationSettingsView:
    row = await ensure_notification_config_row()
    return NotificationSettingsView(
        scheduler_enabled=row.scheduler_enabled,
        interval_hours=row.interval_hours,
        email_recipients=_split_recipients(row.email_recipients),
        sms_recipients=_split_recipients(row.sms_recipients),
        min_relevance_score=row.min_relevance_score,
        last_checked_at=row.last_checked_at,
    )


async def update_notification_settings(
    *,
    scheduler_enabled: bool | None = None,
    interval_hours: int | None = None,
    email_recipients: list[str] | None = None,
    sms_recipients: list[str] | None = None,
    min_relevance_score: float | None = None,
) -> NotificationSettingsView:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NotificationConfig).where(NotificationConfig.id == 1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = NotificationConfig(id=1)
            db.add(row)

        if scheduler_enabled is not None:
            row.scheduler_enabled = scheduler_enabled
        if interval_hours is not None:
            row.interval_hours = max(1, interval_hours)
        if email_recipients is not None:
            row.email_recipients = ",".join(e.strip() for e in email_recipients if e.strip())
        if sms_recipients is not None:
            row.sms_recipients = ",".join(p.strip() for p in sms_recipients if p.strip())
        if min_relevance_score is not None:
            row.min_relevance_score = float(min_relevance_score)

        await db.commit()
        await db.refresh(row)

    return await get_notification_settings()


def _split_recipients(raw: str) -> list[str]:
    return [r.strip() for r in raw.split(",") if r.strip()]


# ─── LLM relevance check ──────────────────────────────────────────────────────


async def _assess_relevance_with_llm(
    title: str, content: str
) -> tuple[bool, float, str]:
    """Return (is_relevant, score 0–1, summary).

    Uses Gemini Flash via google-generativeai.  Falls back gracefully.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        logger.warning("notification_llm_skip: GOOGLE_API_KEY not set")
        return False, 0.0, ""

    prompt = dedent(f"""
        You are a notification relevance evaluator for an Ethiopian tax advisory platform (Awaqi).
        Evaluate whether the following document from the Ministry of Revenue (MoR) is a
        significant public announcement that registered users should be proactively notified about.

        Relevant documents include:
        - New tax laws, proclamations, or directives that affect taxpayers
        - Important deadline notices or regulatory changes
        - New customs duties or VAT updates
        - Official announcements about new obligations or filing procedures

        NOT relevant:
        - Internal administrative documents
        - Routine technical updates with no taxpayer impact
        - Documents that are minor amendments to already-notified changes

        Document title: {title}

        Document content (excerpt):
        {content[:_MAX_CONTENT_CHARS]}

        Respond ONLY with a valid JSON object in this exact format:
        {{
          "is_relevant": true or false,
          "score": 0.0 to 1.0,
          "reason": "one sentence explaining your decision",
          "summary": "2-3 sentence plain-language summary suitable for taxpayers (only if is_relevant is true, otherwise empty string)"
        }}
    """).strip()

    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 512},
        )
        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data: dict[str, Any] = json.loads(raw)
        is_relevant = bool(data.get("is_relevant", False))
        score = float(data.get("score", 0.0))
        summary = str(data.get("summary", ""))
        logger.info(
            "llm_relevance doc_title=%r is_relevant=%s score=%.2f reason=%s",
            title,
            is_relevant,
            score,
            data.get("reason", ""),
        )
        return is_relevant, score, summary
    except Exception:
        logger.exception("llm_relevance_check_failed doc_title=%r", title)
        return False, 0.0, ""


# ─── Email ────────────────────────────────────────────────────────────────────


def _build_email_html(title: str, summary: str, source_url: str | None, sent_at: str) -> str:
    source_section = ""
    if source_url:
        source_section = f"""
        <p style="margin:0 0 12px;">
          <a href="{source_url}" style="color:#1a56db;text-decoration:none;">
            View full document →
          </a>
        </p>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>New Tax Announcement — Awaqi</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#f3f4f6;padding:32px 16px;">
    <tr>
      <td align="center">

        <!-- Card -->
        <table width="600" cellpadding="0" cellspacing="0" role="presentation"
               style="background:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 1px 3px rgba(0,0,0,.12);">

          <!-- Header -->
          <tr>
            <td style="background:#1a56db;padding:28px 32px;">
              <p style="margin:0;color:#ffffff;font-size:12px;letter-spacing:.08em;
                         text-transform:uppercase;opacity:.8;">
                Ethiopian Revenue Authority
              </p>
              <h1 style="margin:6px 0 0;color:#ffffff;font-size:22px;font-weight:700;
                          line-height:1.3;">
                New Tax Announcement
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <h2 style="margin:0 0 16px;font-size:18px;font-weight:600;color:#111827;
                          line-height:1.4;">
                {title}
              </h2>
              <p style="margin:0 0 20px;font-size:15px;color:#374151;line-height:1.6;">
                {summary}
              </p>
              {source_section}
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;"/>
              <p style="margin:0;font-size:13px;color:#6b7280;">
                This notification was sent by <strong>Awaqi</strong>, the AI-powered
                Ethiopian tax advisory platform. You are receiving this because you are
                subscribed to regulatory update notifications.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb;">
              <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;">
                Sent {sent_at} &nbsp;·&nbsp; Awaqi Tax Advisory &nbsp;·&nbsp; Ethiopia
              </p>
            </td>
          </tr>

        </table>
        <!-- /Card -->

      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_email_text(title: str, summary: str, source_url: str | None) -> str:
    lines = [
        "NEW TAX ANNOUNCEMENT — Awaqi",
        "=" * 40,
        "",
        title,
        "",
        summary,
        "",
    ]
    if source_url:
        lines += [f"View full document: {source_url}", ""]
    lines += [
        "---",
        "Awaqi Tax Advisory — Ethiopian Revenue Authority notifications",
    ]
    return "\n".join(lines)


def send_email(
    recipients: list[str],
    subject: str,
    html_body: str,
    text_body: str,
) -> dict[str, str]:
    """Send an email via Mailtrap SMTP. Returns {recipient: 'sent'|error_message}."""
    if not MAILTRAP_USERNAME or not MAILTRAP_PASSWORD:
        logger.warning("email_skip: MAILTRAP_USERNAME/PASSWORD not configured")
        return {r: "skipped: smtp credentials not configured" for r in recipients}

    results: dict[str, str] = {}
    context = ssl.create_default_context()

    for recipient in recipients:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{MAILTRAP_FROM_NAME} <{MAILTRAP_FROM_EMAIL}>"
        msg["To"] = recipient

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(MAILTRAP_HOST, MAILTRAP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(MAILTRAP_USERNAME, MAILTRAP_PASSWORD)
                server.sendmail(MAILTRAP_FROM_EMAIL, recipient, msg.as_string())
            logger.info("email_sent recipient=%r subject=%r", recipient, subject)
            results[recipient] = "sent"
        except Exception as exc:
            logger.exception("email_send_failed recipient=%r", recipient)
            results[recipient] = str(exc)

    return results


# ─── SMS ──────────────────────────────────────────────────────────────────────


def send_sms(phones: list[str], message: str) -> dict[str, str]:
    """Send SMS via GeezSMS. Returns {phone: 'sent'|error_message}."""
    if not GEEZSMS_TOKEN:
        logger.warning("sms_skip: GEEZSMS_TOKEN not configured")
        return {p: "skipped: sms token not configured" for p in phones}

    results: dict[str, str] = {}

    for phone in phones:
        try:
            resp = httpx.post(
                GEEZSMS_API_URL,
                data={
                    "token": GEEZSMS_TOKEN,
                    "phone": phone,
                    "msg": message,
                    **({"shortcode_id": GEEZSMS_SHORTCODE_ID} if GEEZSMS_SHORTCODE_ID else {}),
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("message_status") == "success":
                logger.info("sms_sent phone=%r log_id=%s", phone, data.get("api_log_id"))
                results[phone] = "sent"
            else:
                msg = str(data)
                logger.warning("sms_api_error phone=%r response=%s", phone, msg)
                results[phone] = f"api_error: {msg}"
        except Exception as exc:
            logger.exception("sms_send_failed phone=%r", phone)
            results[phone] = str(exc)

    return results


# ─── Orchestration ────────────────────────────────────────────────────────────


async def check_and_send_notifications(
    trigger: str = "scheduled",
) -> dict[str, int]:
    """Main entry-point called by the RQ job and the scheduler.

    Returns stats dict with counts of relevant docs found and notifications sent.
    """
    stats: dict[str, int] = {
        "docs_checked": 0,
        "docs_relevant": 0,
        "emails_sent": 0,
        "emails_failed": 0,
        "sms_sent": 0,
        "sms_failed": 0,
    }

    settings = await get_notification_settings()
    if not settings.email_recipients and not settings.sms_recipients:
        logger.info("notification_skip: no recipients configured")
        return stats

    # Query documents indexed after the watermark
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Document)
            .where(Document.status == DocumentStatus.INDEXED)
            .order_by(Document.updated_at.asc())
        )
        if settings.last_checked_at is not None:
            stmt = stmt.where(Document.updated_at > settings.last_checked_at)

        result = await db.execute(stmt)
        docs = result.scalars().all()

        if not docs:
            logger.info("notification_check: no new indexed documents since %s", settings.last_checked_at)
            _advance_watermark()
            return stats

        logger.info("notification_check: found %d new document(s) to evaluate", len(docs))
        now = datetime.now(timezone.utc)

        for doc in docs:
            stats["docs_checked"] += 1

            # Fetch first N chunks for LLM evaluation
            chunk_result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc.id)
                .order_by(DocumentChunk.chunk_index.asc())
                .limit(_EVAL_CHUNKS)
            )
            chunks = chunk_result.scalars().all()
            content = "\n\n".join(c.content for c in chunks)

            is_relevant, score, summary = await _assess_relevance_with_llm(doc.title, content)

            if not is_relevant or score < settings.min_relevance_score:
                logger.info(
                    "notification_skip doc=%s score=%.2f threshold=%.2f",
                    doc.id,
                    score,
                    settings.min_relevance_score,
                )
                continue

            stats["docs_relevant"] += 1

            # Write in-app announcement so the user portal can display it
            announcement = Announcement(
                id=uuid.uuid4(),
                doc_id=doc.id,
                doc_title=doc.title[:512],
                summary=summary,
                source_url=doc.source_url,
                trigger=trigger,
            )
            db.add(announcement)

            subject = f"New Tax Announcement: {doc.title[:80]}"
            sent_at = now.strftime("%B %d, %Y at %H:%M UTC")

            html_body = _build_email_html(doc.title, summary, doc.source_url, sent_at)
            text_body = _build_email_text(doc.title, summary, doc.source_url)
            sms_text = _build_sms_text(doc.title, summary)

            # Send emails
            if settings.email_recipients:
                email_results = send_email(
                    settings.email_recipients, subject, html_body, text_body
                )
                for recipient, status in email_results.items():
                    ok = status == "sent"
                    if ok:
                        stats["emails_sent"] += 1
                    else:
                        stats["emails_failed"] += 1
                    log = NotificationLog(
                        id=uuid.uuid4(),
                        doc_id=doc.id,
                        doc_title=doc.title[:512],
                        channel="email",
                        recipient=recipient,
                        subject=subject,
                        summary=summary,
                        status="sent" if ok else "failed",
                        error=None if ok else status,
                        trigger=trigger,
                    )
                    db.add(log)

            # Send SMS
            if settings.sms_recipients:
                sms_results = send_sms(settings.sms_recipients, sms_text)
                for phone, status in sms_results.items():
                    ok = status == "sent"
                    if ok:
                        stats["sms_sent"] += 1
                    else:
                        stats["sms_failed"] += 1
                    log = NotificationLog(
                        id=uuid.uuid4(),
                        doc_id=doc.id,
                        doc_title=doc.title[:512],
                        channel="sms",
                        recipient=phone,
                        subject=None,
                        summary=sms_text,
                        status="sent" if ok else "failed",
                        error=None if ok else status,
                        trigger=trigger,
                    )
                    db.add(log)

        # Advance watermark to latest doc's updated_at
        if docs:
            new_watermark = max(d.updated_at for d in docs)
            config_result = await db.execute(
                select(NotificationConfig).where(NotificationConfig.id == 1)
            )
            config_row = config_result.scalar_one_or_none()
            if config_row is not None:
                config_row.last_checked_at = new_watermark

        await db.commit()

    logger.info("notification_run trigger=%s stats=%s", trigger, stats)
    return stats


def _advance_watermark() -> None:
    """No-op placeholder for the empty-docs path (watermark stays unchanged)."""


def _build_sms_text(title: str, summary: str) -> str:
    """Build a short SMS-friendly message (keep under 160 chars where possible)."""
    short_title = title[:60] + ("…" if len(title) > 60 else "")
    short_summary = summary[:90] + ("…" if len(summary) > 90 else "")
    return f"[Awaqi] New MoR announcement: {short_title}. {short_summary}"


# ─── Notification log queries ─────────────────────────────────────────────────


async def list_notification_logs(
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[NotificationLog], int]:
    from sqlalchemy import func

    async with AsyncSessionLocal() as db:
        total = int(
            await db.scalar(
                select(func.count()).select_from(NotificationLog)
            )
            or 0
        )
        result = await db.execute(
            select(NotificationLog)
            .order_by(NotificationLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.scalars().all()
    return list(rows), total


# ─── Announcement queries (in-app feed) ───────────────────────────────────────


async def list_announcements(
    limit: int = 20,
    since: datetime | None = None,
) -> list[Announcement]:
    """Return recent announcements for the user portal feed."""
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Announcement)
            .order_by(Announcement.created_at.desc())
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(Announcement.created_at > since)
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def count_announcements_since(since: datetime) -> int:
    """Count announcements created after ``since`` (for unread badge)."""
    from sqlalchemy import func

    async with AsyncSessionLocal() as db:
        count = await db.scalar(
            select(func.count())
            .select_from(Announcement)
            .where(Announcement.created_at > since)
        )
    return int(count or 0)
