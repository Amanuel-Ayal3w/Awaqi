import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

from ai_engine.ingest import ingest_bytes_for_document, ingest_plain_text
from ai_engine.web_scraper import WebScraper
from database import get_session, ping_redis
from database.models.auth import BaUser
from database.models.customer import CuUser
from database.models.document import Document, DocumentChunk
from database.models.document import DocumentStatus as DocStatusEnum
from database.models.session import ChatSession, Message, MessageRole
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_admin
from apps.api.schemas import (
    AdminAnalytics,
    AdminDocumentDetail,
    AdminDocumentItem,
    AdminDocumentList,
    AdminDocumentPatch,
    AdminSystemHealth,
    AdminUserItem,
    AdminUserList,
    AdminUserPatch,
    DocumentStatus,
    DocumentStatusCount,
    LogEntry,
    LogEntryList,
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
UPLOAD_READ_CHUNK_SIZE = 1024 * 1024
ALLOWED_UPLOAD_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "text/plain",
    "text/html",
    "application/xhtml+xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}
ALLOWED_EXTENSIONS = (".pdf", ".txt", ".html", ".htm", ".docx")

router = APIRouter()


def _document_item_from_row(
    doc: Document,
    uploader_email: str | None,
    uploader_name: str | None,
) -> AdminDocumentItem:
    return AdminDocumentItem(
        id=str(doc.id),
        title=doc.title,
        status=str(getattr(doc.status, "value", doc.status)),
        source_url=doc.source_url,
        created_at=doc.created_at.isoformat(),
        processing_stage=doc.processing_stage,
        ingest_error=doc.ingest_error,
        byte_size=doc.byte_size,
        uploaded_by_id=str(doc.uploaded_by_id) if doc.uploaded_by_id else None,
        uploaded_by_email=uploader_email,
        uploaded_by_name=uploader_name,
    )


def _document_detail_from_row(
    doc: Document,
    uploader_email: str | None,
    uploader_name: str | None,
) -> AdminDocumentDetail:
    it = _document_item_from_row(doc, uploader_email, uploader_name)
    return AdminDocumentDetail(
        **it.model_dump(),
        file_hash=doc.file_hash,
        registry_key=doc.registry_key,
    )


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
    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in ALLOWED_UPLOAD_MIME_TYPES:
        # Extension is authoritative when browsers mislabel MIME.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported content type for this file extension",
        )


def _guess_mime(filename: str | None, content_type: str | None) -> str:
    if content_type:
        return content_type.split(";")[0].strip().lower()
    fn = (filename or "").lower()
    if fn.endswith(".pdf"):
        return "application/pdf"
    if fn.endswith(".txt"):
        return "text/plain"
    if fn.endswith(".html") or fn.endswith(".htm"):
        return "text/html"
    if fn.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


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
    uploaded_by: str | None = Query(
        None,
        description="Filter by uploader ba_user UUID (superadmin only).",
    ),
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    safe_limit = max(1, min(limit, 500))
    stmt = (
        select(Document, BaUser.email, BaUser.name)
        .outerjoin(BaUser, Document.uploaded_by_id == BaUser.id)
        .order_by(Document.created_at.desc())
        .limit(safe_limit)
    )
    if uploaded_by is not None:
        _require_superadmin(current_user)
        try:
            uploader_filter = uuid.UUID(uploaded_by)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="uploaded_by must be a valid UUID",
            )
        stmt = stmt.where(Document.uploaded_by_id == uploader_filter)

    result = await db.execute(stmt)
    rows = result.all()

    return AdminDocumentList(
        documents=[
            _document_item_from_row(doc, email, name) for doc, email, name in rows
        ]
    )


@router.get("/admin/analytics", response_model=AdminAnalytics)
async def admin_analytics(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    documents_total = await db.scalar(select(func.count()).select_from(Document)) or 0
    status_rows = (
        await db.execute(
            select(Document.status, func.count())
            .select_from(Document)
            .group_by(Document.status)
        )
    ).all()
    documents_by_status = [
        DocumentStatusCount(status=str(getattr(s, "value", s)), count=int(c))
        for s, c in status_rows
    ]
    chunks_total = await db.scalar(select(func.count()).select_from(DocumentChunk)) or 0
    admin_users_total = await db.scalar(select(func.count()).select_from(BaUser)) or 0
    customer_users_total = await db.scalar(select(func.count()).select_from(CuUser)) or 0
    chat_sessions_total = (
        await db.scalar(select(func.count()).select_from(ChatSession)) or 0
    )
    messages_total = await db.scalar(select(func.count()).select_from(Message)) or 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    messages_last_7_days = (
        await db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.created_at >= cutoff)
        )
        or 0
    )
    return AdminAnalytics(
        documents_total=int(documents_total),
        documents_by_status=documents_by_status,
        chunks_total=int(chunks_total),
        admin_users_total=int(admin_users_total),
        customer_users_total=int(customer_users_total),
        chat_sessions_total=int(chat_sessions_total),
        messages_total=int(messages_total),
        messages_last_7_days=int(messages_last_7_days),
    )


@router.get("/admin/system-health", response_model=AdminSystemHealth)
async def admin_system_health(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("system_health_db_ping_failed")

    t0 = time.perf_counter()
    redis_ok = await ping_redis()
    redis_ms = (time.perf_counter() - t0) * 1000.0

    return AdminSystemHealth(
        database_ok=db_ok,
        redis_ok=bool(redis_ok),
        redis_latency_ms=redis_ms if redis_ok else None,
    )


@router.get("/admin/documents/{doc_id}", response_model=AdminDocumentDetail)
async def get_admin_document(
    doc_id: str,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id must be a valid UUID",
        )
    result = await db.execute(
        select(Document, BaUser.email, BaUser.name)
        .outerjoin(BaUser, Document.uploaded_by_id == BaUser.id)
        .where(Document.id == uid)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc, email, name = row
    return _document_detail_from_row(doc, email, name)


@router.patch("/admin/documents/{doc_id}", response_model=AdminDocumentDetail)
async def patch_admin_document(
    doc_id: str,
    patch: AdminDocumentPatch,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    _require_superadmin(current_user)
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id must be a valid UUID",
        )
    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    data = patch.model_dump(exclude_unset=True)
    if "uploaded_by_id" in data:
        val = data["uploaded_by_id"]
        if val is None or val == "":
            doc.uploaded_by_id = None
        else:
            try:
                new_uploader = uuid.UUID(val)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="uploaded_by_id must be a valid UUID",
                )
            exists = await db.scalar(select(BaUser.id).where(BaUser.id == new_uploader))
            if exists is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploader user not found",
                )
            doc.uploaded_by_id = new_uploader

    await db.commit()
    await db.refresh(doc)
    row = (
        await db.execute(
            select(Document, BaUser.email, BaUser.name)
            .outerjoin(BaUser, Document.uploaded_by_id == BaUser.id)
            .where(Document.id == uid)
        )
    ).one()
    d2, email, name = row
    return _document_detail_from_row(d2, email, name)


@router.post("/admin/documents/{doc_id}/ingest-text", response_model=DocumentStatus)
async def ingest_document_plain_text(
    doc_id: str,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
    payload: str = Body(..., media_type="text/plain"),
):
    """Upload corrected UTF-8 plain text to re-index a document (AWA-9)."""
    del current_user
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id must be a valid UUID",
        )
    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        n = await ingest_plain_text(db, doc, payload)
        logger.info("ingest-text doc=%s chunks=%d", doc.id, n)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    await db.refresh(doc)
    return DocumentStatus(
        doc_id=str(doc.id),
        status=str(getattr(doc.status, "value", doc.status)),
        processing_stage=doc.processing_stage,
        ingest_error=doc.ingest_error,
    )


@router.post("/admin/scrape")
async def trigger_scrape(
    current_user: BaUser = Depends(get_current_admin),
):
    """Run one MoR scrape cycle immediately (AWA-11)."""
    _require_superadmin(current_user)
    stats = await WebScraper().scan_for_updates()
    return {"status": "ok", "stats": stats}


@router.get("/admin/users", response_model=AdminUserList)
async def list_admin_users(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    _require_superadmin(current_user)
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


@router.patch("/admin/users/{user_id}", response_model=AdminUserItem)
async def patch_admin_user(
    user_id: str,
    patch: AdminUserPatch,
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

    result = await db.execute(select(BaUser).where(BaUser.id == target_uuid))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    data = patch.model_dump(exclude_unset=True)
    if "role" in data:
        r = data["role"]
        if r not in ("superadmin", "editor"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="role must be superadmin or editor",
            )
        target.role = r
    if "is_active" in data:
        if target_uuid == current_user.id and not data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )
        target.is_active = bool(data["is_active"])

    if not data:
        pass  # no-op

    await db.commit()
    await db.refresh(target)
    return AdminUserItem(
        id=str(target.id),
        name=target.name,
        email=target.email,
        role=str(getattr(target.role, "value", target.role)),
        is_active=bool(target.is_active),
        created_at=target.created_at.isoformat(),
    )


@router.post("/admin/upload", response_model=DocumentStatus)
async def upload_document(
    file: UploadFile = File(...),
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
    overwrite: bool = Query(False),
):
    _validate_upload_metadata(file)
    file_hash = await _sha256_with_size_limit(file)

    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    existing_doc = existing.scalar_one_or_none()

    duplicate: bool = False
    if existing_doc is not None and not overwrite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate",
                "duplicate_of": str(existing_doc.id),
                "choices": ["cancel", "overwrite"],
            },
        )

    if existing_doc is not None and overwrite:
        doc = existing_doc
        doc.title = (file.filename or doc.title)[:512]
        doc.uploaded_by_id = current_user.id
        duplicate = True
    else:
        doc = Document(
            id=uuid.uuid4(),
            title=(file.filename or "Untitled")[:512],
            file_hash=file_hash,
            status=DocStatusEnum.PENDING,
            uploaded_by_id=current_user.id,
        )
        db.add(doc)
        await db.flush()

    try:
        pdf_bytes = await file.read()
        await ingest_bytes_for_document(
            db,
            doc,
            pdf_bytes,
            mime_type=_guess_mime(file.filename, file.content_type),
            filename=file.filename,
            genai_client=None,
        )
        await db.refresh(doc)
        logger.info(
            "Document %s ingest finished status=%s",
            doc.id,
            getattr(doc.status, "value", doc.status),
        )
    except ValueError as e:
        await db.refresh(doc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception:
        logger.exception("Ingestion failed for document %s", doc.id)
        await db.refresh(doc)
        raise

    return DocumentStatus(
        doc_id=str(doc.id),
        status=str(getattr(doc.status, "value", doc.status)),
        duplicate=duplicate,
        processing_stage=doc.processing_stage,
        ingest_error=doc.ingest_error,
    )


@router.get("/admin/logs", response_model=LogEntryList)
async def get_logs(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    """Return recent chat activity for admin monitoring."""
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

