import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone

from ai_engine import ingest_pdf
from database import get_session
from database.models.auth import BaUser
from database.models.document import Document
from database.models.document import DocumentStatus as DocStatusEnum
from database.models.session import Message, MessageRole
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
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
UPLOAD_READ_CHUNK_SIZE = 1024 * 1024
ALLOWED_UPLOAD_MIME_TYPES = {"application/pdf", "application/x-pdf"}

router = APIRouter()


def _role_value(user: BaUser) -> str:
    return str(getattr(user.role, "value", user.role))


def _require_superadmin(user: BaUser) -> None:
    if _role_value(user) != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin role is required for this action",
        )


def _validate_upload_metadata(file: UploadFile) -> None:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted",
        )
    if file.content_type and file.content_type not in ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported content type; expected application/pdf",
        )


async def _sha256_with_size_limit(file: UploadFile) -> str:
    total_bytes = 0
    digest = hashlib.sha256()
    while chunk := await file.read(UPLOAD_READ_CHUNK_SIZE):
        total_bytes += len(chunk)
        if total_bytes > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds max allowed size of {MAX_UPLOAD_BYTES} bytes",
            )
        digest.update(chunk)
    await file.seek(0)
    return digest.hexdigest()


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
    _require_superadmin(current_user)

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
    _require_superadmin(current_user)
    _validate_upload_metadata(file)
    file_hash = await _sha256_with_size_limit(file)

    # Check for duplicate by file hash
    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    doc = existing.scalar_one_or_none()

    if doc is not None:
        return DocumentStatus(
            doc_id=str(doc.id),
            status=str(getattr(doc.status, "value", doc.status)),
        )

    # Create new document record
    doc = Document(
        id=uuid.uuid4(),
        title=file.filename or "Untitled",
        file_hash=file_hash,
        status=DocStatusEnum.PENDING,
    )
    db.add(doc)
    await db.flush()

    # Run the ingestion pipeline: extract → chunk → embed → store
    try:
        pdf_bytes = await file.read()
        chunk_count = await ingest_pdf(pdf_bytes, doc.id, db)
        doc.status = DocStatusEnum.INDEXED
        logger.info("Document %s indexed with %d chunks", doc.id, chunk_count)
    except Exception:
        doc.status = DocStatusEnum.FAILED
        logger.exception("Ingestion failed for document %s", doc.id)

    return DocumentStatus(
        doc_id=str(doc.id),
        status=str(getattr(doc.status, "value", doc.status)),
    )


@router.get("/admin/logs", response_model=LogEntryList)
async def get_logs(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    """Return recent chat activity for admin monitoring."""
    from database.models.session import ChatSession

    result = await db.execute(
        select(Message, ChatSession)
        .join(ChatSession, Message.session_id == ChatSession.id)
        .order_by(Message.created_at.desc())
        .limit(100)
    )
    rows = result.all()

    logs = [
        LogEntry(
            timestamp=msg.created_at.isoformat(),
            level="INFO" if msg.role == MessageRole.USER else "DEBUG",
            message=(
                f"[session:{str(session.id)[:8]}] "
                f"[{msg.role.value}] "
                f"{msg.content[:120]}"
            ),
        )
        for msg, session in rows
    ]

    if not logs:
        logs = [
            LogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level="INFO",
                message="No chat activity recorded yet.",
            )
        ]

    return LogEntryList(logs=logs)

