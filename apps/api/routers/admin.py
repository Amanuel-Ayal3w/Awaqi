import hashlib
import json
import uuid
from datetime import datetime, timezone

from database import get_session
from database.models.auth import BaUser
from database.models.document import Document
from database.models.document import DocumentStatus as DocStatusEnum
from database.models.session import Message, MessageRole
from database.redis_client import redis_client
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_admin
from apps.api.schemas import (
    AdminDocumentItem,
    AdminDocumentList,
    AdminUserItem,
    AdminUserList,
    DocumentStatus,
    LogEntry,
    LogEntryList,
    ScraperJobStatus,
    ScraperStatus,
)

REDIS_TRIGGER_KEY = "scraper:trigger"
REDIS_LOCK_KEY = "scraper:running"
REDIS_JOB_PREFIX = "scraper:job:"

router = APIRouter()


@router.get("/admin/documents", response_model=AdminDocumentList)
async def list_admin_documents(
    limit: int = 100,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user  # endpoint is admin-protected via dependency
    safe_limit = max(1, min(limit, 500))

    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).limit(safe_limit)
    )
    documents = result.scalars().all()

    return AdminDocumentList(
        documents=[
            AdminDocumentItem(
                id=str(doc.id),
                title=doc.title,
                status=str(getattr(doc.status, "value", doc.status)),
                source_url=doc.source_url,
                created_at=doc.created_at.isoformat(),
            )
            for doc in documents
        ]
    )


@router.get("/admin/users", response_model=AdminUserList)
async def list_admin_users(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(BaUser).order_by(BaUser.created_at.desc())
    )
    users = result.scalars().all()

    return AdminUserList(
        users=[
            AdminUserItem(
                id=str(user.id),
                name=user.name,
                email=user.email,
                role=str(getattr(user.role, "value", user.role)),
                is_active=bool(user.is_active),
                created_at=user.created_at.isoformat(),
            )
            for user in users
        ]
    )


@router.delete("/admin/users/{user_id}")
async def delete_admin_user(
    user_id: str,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a valid UUID",
        )

    if target_uuid == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    result = await db.execute(select(BaUser).where(BaUser.id == target_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    return {"status": "ok", "deleted_user_id": user_id}


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
    is_running = await redis_client.get(REDIS_LOCK_KEY)
    if is_running:
        return ScraperStatus(job_id="", status="already_running")

    job_id = str(uuid.uuid4())
    await redis_client.set(
        REDIS_TRIGGER_KEY,
        json.dumps({"job_id": job_id, "requested_at": datetime.now(timezone.utc).isoformat()}),
    )
    return ScraperStatus(job_id=job_id, status="queued")


@router.get("/admin/scrape/status", response_model=ScraperJobStatus)
async def get_scrape_status(
    job_id: str,
    current_user: BaUser = Depends(get_current_admin),
):
    raw = await redis_client.get(f"{REDIS_JOB_PREFIX}{job_id}")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired",
        )
    data = json.loads(raw)
    return ScraperJobStatus(**data)
