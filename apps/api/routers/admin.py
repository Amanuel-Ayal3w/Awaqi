import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_admin
from apps.api.schemas import (
    AdminUserItem,
    AdminUserList,
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
    # TODO: dispatch a real scraper job (e.g. publish to Redis queue)
    # from apps.scraper import trigger_job
    # job_id = await trigger_job()
    job_id = str(uuid.uuid4())
    return ScraperStatus(job_id=job_id, status="queued")
