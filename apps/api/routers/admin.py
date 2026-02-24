import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_admin
from apps.api.schemas import (
    DocumentStatus,
    LogEntry,
    LogEntryList,
    ScraperStatus,
)
from database import get_session
from database.models.auth import BaUser
from database.models.document import Document, DocumentStatus as DocStatusEnum
from database.models.session import Message, MessageRole

router = APIRouter()


@router.post("/admin/upload", response_model=DocumentStatus)
async def upload_document(
    file: UploadFile = File(...),
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate by file hash
    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    doc = existing.scalar_one_or_none()

    if doc is None:
        doc = Document(
            id=uuid.uuid4(),
            title=file.filename or "Untitled",
            file_hash=file_hash,
            status=DocStatusEnum.PENDING,
        )
        db.add(doc)
        await db.flush()

    return DocumentStatus(doc_id=str(doc.id), status=doc.status)


@router.get("/admin/logs", response_model=LogEntryList)
async def get_logs(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(Message)
        .where(Message.role == MessageRole.USER)
        .order_by(Message.created_at.desc())
        .limit(100)
    )
    messages = result.scalars().all()

    logs = [
        LogEntry(
            timestamp=msg.created_at.isoformat(),
            level="INFO",
            message=f"[{msg.role}] {msg.content[:120]}",
        )
        for msg in messages
    ]

    # Prepend a system startup entry so the page is never empty
    if not logs:
        logs = [
            LogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level="INFO",
                message="No messages recorded yet.",
            )
        ]

    return LogEntryList(logs=logs)


@router.post("/admin/scrape", response_model=ScraperStatus)
async def trigger_scrape(
    current_user: BaUser = Depends(get_current_admin),
):
    # TODO: dispatch a real scraper job (e.g. publish to Redis queue)
    # from apps.scraper import trigger_job
    # job_id = await trigger_job()
    job_id = str(uuid.uuid4())
    return ScraperStatus(job_id=job_id, status="queued")
