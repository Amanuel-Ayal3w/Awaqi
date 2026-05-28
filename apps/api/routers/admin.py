import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

from ai_engine.ingest import ingest_bytes_for_document, ingest_plain_text
from ai_engine.thumbnail import generate_pdf_thumbnail, thumbnail_path_for_document
from database import get_session, ping_redis
from database.vector_store_admin import (
    delete_all_document_chunks,
    get_vector_store_stats,
    wipe_vector_embeddings,
)
from database.models.auth import BaUser
from database.models.customer import CuUser
from database.models.document import Document, DocumentChunk
from database.models.document import DocumentStatus as DocStatusEnum
from database.models.document import EnforcementStatus as EnforcementStatusEnum
from database.models.session import ChatSession, Message, MessageRole
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_admin
from apps.api.queue.jobs.ingest_job import run_ingest_job
from apps.api.queue.jobs.mor_scraper_job import run_mor_scrape_job
from apps.api.queue.jobs.telegram_job import run_telegram_scrape_job
from apps.api.queue.progress import publish_progress
from apps.api.queue.queues import ingest_queue, scraper_queue
from apps.api.document_preview import build_content_preview, get_document_or_404, load_document_bytes
from apps.api.scraper_scheduler import apply_scheduler_config, get_next_run_time
from apps.api.telegram_scheduler import apply_telegram_scheduler_config, get_telegram_next_run_time
from apps.api.scraper_service import (
    get_last_scraper_run,
    get_scraper_settings,
    list_scraper_runs,
    update_scraper_settings,
)
from apps.api.telegram_service import (
    get_telegram_settings,
    clear_telegram_messages,
    delete_telegram_message,
    list_telegram_messages,
    list_telegram_runs,
    reingest_telegram_message,
    update_telegram_settings,
)
from apps.api.schemas import (
    AdminAnalytics,
    AdminDocumentContentPreview,
    AdminDocumentDetail,
    AdminDocumentItem,
    AdminDocumentList,
    AdminDocumentPatch,
    AdminJobEnqueued,
    AdminNotificationConfig,
    AdminNotificationConfigPatch,
    AdminNotificationLogItem,
    AdminNotificationLogList,
    AdminNotificationTriggerResult,
    ExtractedPagePreview,
    AdminScrapeStats,
    AdminScraperConfig,
    AdminScraperConfigPatch,
    AdminScraperRunItem,
    AdminScraperRunList,
    AdminScraperStatus,
    AdminSystemHealth,
    AdminVectorStoreActionResult,
    AdminVectorStoreStats,
    AdminTelegramConfig,
    AdminTelegramConfigPatch,
    AdminTelegramClearResult,
    AdminTelegramMessageItem,
    AdminTelegramMessageList,
    AdminTelegramRunItem,
    AdminTelegramRunList,
    AdminTelegramScrapeStats,
    AdminUserItem,
    AdminUserList,
    AdminUserPatch,
    DocumentStatus,
    DocumentStatusCount,
    LogEntry,
    LogEntryList,
    TelegramScrapeRequest,
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
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/octet-stream",
}
ALLOWED_EXTENSIONS = (".pdf", ".txt", ".html", ".htm", ".docx")

router = APIRouter()


def _document_item_from_row(
    doc: Document,
    uploader_email: str | None,
    uploader_name: str | None,
) -> AdminDocumentItem:
    enforcement = getattr(doc, "enforcement_status", None)
    return AdminDocumentItem(
        id=str(doc.id),
        title=doc.title,
        status=str(getattr(doc.status, "value", doc.status)),
        enforcement_status=str(getattr(enforcement, "value", enforcement) or "in_effect"),
        source_url=doc.source_url,
        source_system=doc.source_system,
        storage_path=doc.storage_path,
        thumbnail_url=f"/v1/admin/documents/{doc.id}/thumbnail",
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
        storage_path=doc.storage_path,
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
    offset: int = 0,
    scraped_only: bool = Query(
        False, description="When true, only documents with a source_url (scraper)."
    ),
    uploaded_by: str | None = Query(
        None,
        description="Filter by uploader ba_user UUID (superadmin only).",
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by document status (e.g. requires_manual_review, indexed, failed).",
    ),
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    safe_limit = max(1, min(limit, 500))
    safe_offset = max(0, offset)
    uploader_filter: uuid.UUID | None = None
    if uploaded_by is not None:
        _require_superadmin(current_user)
        try:
            uploader_filter = uuid.UUID(uploaded_by)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="uploaded_by must be a valid UUID",
            )

    count_stmt = select(func.count()).select_from(Document)
    if scraped_only:
        count_stmt = count_stmt.where(Document.source_url.isnot(None))
    if uploader_filter is not None:
        count_stmt = count_stmt.where(Document.uploaded_by_id == uploader_filter)
    if status_filter is not None:
        count_stmt = count_stmt.where(Document.status == status_filter)
    total = int(await db.scalar(count_stmt) or 0)

    stmt = (
        select(Document, BaUser.email, BaUser.name)
        .outerjoin(BaUser, Document.uploaded_by_id == BaUser.id)
        .order_by(Document.created_at.desc())
        .offset(safe_offset)
        .limit(safe_limit)
    )
    if scraped_only:
        stmt = stmt.where(Document.source_url.isnot(None))
    if uploader_filter is not None:
        stmt = stmt.where(Document.uploaded_by_id == uploader_filter)
    if status_filter is not None:
        stmt = stmt.where(Document.status == status_filter)

    result = await db.execute(stmt)
    rows = result.all()

    return AdminDocumentList(
        documents=[
            _document_item_from_row(doc, email, name) for doc, email, name in rows
        ],
        total=total,
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


@router.get("/admin/vector-store", response_model=AdminVectorStoreStats)
async def admin_vector_store_stats(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    stats = await get_vector_store_stats(db)
    return AdminVectorStoreStats(**stats.to_dict())


@router.delete(
    "/admin/vector-store/embeddings",
    response_model=AdminVectorStoreActionResult,
)
async def admin_vector_store_wipe_embeddings(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    _require_superadmin(current_user)
    affected = await wipe_vector_embeddings(db)
    return AdminVectorStoreActionResult(
        action="wipe_embeddings",
        affected_rows=affected,
        message=(
            f"Cleared embeddings on {affected} chunk(s). "
            "Re-run document ingest to rebuild vectors with the current model."
        ),
    )


@router.delete(
    "/admin/vector-store/chunks",
    response_model=AdminVectorStoreActionResult,
)
async def admin_vector_store_delete_chunks(
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    _require_superadmin(current_user)
    affected = await delete_all_document_chunks(db)
    return AdminVectorStoreActionResult(
        action="delete_chunks",
        affected_rows=affected,
        message=(
            f"Deleted {affected} document chunk row(s). "
            "Documents remain; re-ingest to restore searchable content."
        ),
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

    if "enforcement_status" in data and data["enforcement_status"] is not None:
        try:
            doc.enforcement_status = EnforcementStatusEnum(data["enforcement_status"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="enforcement_status must be 'in_effect' or 'draft'",
            )

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


@router.get("/admin/documents/{doc_id}/content", response_model=AdminDocumentContentPreview)
async def get_admin_document_content(
    doc_id: str,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    try:
        doc = await get_document_or_404(db, doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id must be a valid UUID",
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    payload = await build_content_preview(db, doc)
    return AdminDocumentContentPreview(
        pages=[ExtractedPagePreview(**p) for p in payload["pages"]],
        **{k: v for k, v in payload.items() if k != "pages"},
    )


@router.get("/admin/documents/{doc_id}/file")
async def download_admin_document_file(
    doc_id: str,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    try:
        doc = await get_document_or_404(db, doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id must be a valid UUID",
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    from ai_engine.scraper.storage import document_storage_root, guess_media_type

    if doc.storage_path:
        path = document_storage_root() / doc.storage_path
        if path.is_file():
            media_type = guess_media_type(doc.storage_path)
            return FileResponse(
                path,
                media_type=media_type,
                filename=doc.storage_path,
            )

    if not doc.source_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stored PDF or source URL",
        )

    import httpx

    from ai_engine.scraper.mor_http import USER_AGENT, mor_http_verify

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        verify=mor_http_verify(),
        timeout=120.0,
    ) as client:
        from ai_engine.scraper.http_retry import fetch_with_retry

        resp = await fetch_with_retry(client, doc.source_url)
        return Response(
            content=resp.content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{doc.id}.pdf"'},
        )


@router.get("/admin/documents/{doc_id}/thumbnail")
async def get_admin_document_thumbnail(
    doc_id: str,
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    try:
        doc = await get_document_or_404(db, doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id must be a valid UUID",
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not doc.storage_path or not doc.storage_path.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail is available only for stored PDF documents",
        )

    thumb_path = thumbnail_path_for_document(str(doc.id))
    if not thumb_path.is_file():
        try:
            thumb_path = generate_pdf_thumbnail(
                doc_id=str(doc.id),
                storage_path=doc.storage_path,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored file not found",
            )
        except Exception:
            logger.exception("thumbnail_generation_failed doc_id=%s", doc.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate thumbnail",
            )

    return FileResponse(
        path=thumb_path,
        media_type="image/jpeg",
        filename=f"{doc.id}.jpg",
    )


@router.post("/admin/documents/{doc_id}/retry-ingest", response_model=DocumentStatus)
async def retry_admin_document_ingest(
    doc_id: str,
    force_index: bool = Query(
        False,
        description="When true, index even if OCR confidence is below threshold.",
    ),
    current_user: BaUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    del current_user
    try:
        doc = await get_document_or_404(db, doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id must be a valid UUID",
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    from ai_engine.scraper.storage import guess_media_type

    file_bytes = await load_document_bytes(doc)
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stored file on disk for this document",
        )

    mime = guess_media_type(doc.storage_path)
    filename = doc.storage_path or f"{doc.id}.bin"

    try:
        n = await ingest_bytes_for_document(
            db,
            doc,
            file_bytes,
            mime_type=mime,
            filename=filename,
            genai_client=None,
            force_index=force_index,
        )
        logger.info("retry-ingest doc=%s chunks=%d force_index=%s", doc.id, n, force_index)
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


def _scrape_stats_from_dict(raw: dict | None) -> AdminScrapeStats:
    if not raw:
        return AdminScrapeStats()
    return AdminScrapeStats(
        discovered=int(raw.get("discovered", 0)),
        inserted=int(raw.get("inserted", 0)),
        skipped=int(raw.get("skipped", 0)),
        errors=int(raw.get("errors", 0)),
    )


def _run_to_item(run) -> AdminScraperRunItem:
    return AdminScraperRunItem(
        id=str(run.id),
        trigger=str(run.trigger),
        status=str(run.status),
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        stats=_scrape_stats_from_dict(run.stats if isinstance(run.stats, dict) else None),
        error_message=run.error_message,
    )


@router.post("/admin/scrape", response_model=AdminJobEnqueued)
async def trigger_scrape(
    request: Request,
    current_user: BaUser = Depends(get_current_admin),
):
    """Enqueue a MoR scrape cycle via Redis Queue and return the job_id immediately (AWA-11)."""
    _require_superadmin(current_user)
    job_id = str(uuid.uuid4())
    publish_progress(job_id, 0, "Queued", "queued")
    scraper_queue.enqueue(
        run_mor_scrape_job,
        job_id,
        "manual",
        None,
        None,
        job_id=job_id,
    )
    return AdminJobEnqueued(
        job_id=job_id,
        status="queued",
        message="MoR scrape job enqueued. Connect to /v1/progress/{job_id} for live progress.",
    )


@router.get("/admin/scraper/status", response_model=AdminScraperStatus)
async def scraper_status(
    request: Request,
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    settings = await get_scraper_settings()
    last = await get_last_scraper_run()
    return AdminScraperStatus(
        scheduler_enabled=settings.scheduler_enabled,
        cron_hour=settings.cron_hour,
        cron_minute=settings.cron_minute,
        timezone="Africa/Addis_Ababa",
        next_run_time=get_next_run_time(request.app),
        last_run=_run_to_item(last) if last else None,
    )


@router.get("/admin/scraper/runs", response_model=AdminScraperRunList)
async def scraper_runs(
    limit: int = Query(20, ge=1, le=100),
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    runs = await list_scraper_runs(limit=limit)
    return AdminScraperRunList(runs=[_run_to_item(r) for r in runs])


@router.get("/admin/scraper/config", response_model=AdminScraperConfig)
async def scraper_config_get(
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    s = await get_scraper_settings()
    return AdminScraperConfig(
        seed_urls=s.seed_urls,
        scheduler_enabled=s.scheduler_enabled,
        cron_hour=s.cron_hour,
        cron_minute=s.cron_minute,
        max_links=s.max_links,
        storage_dir=s.storage_dir,
        api_base_url=s.api_base_url,
    )


@router.patch("/admin/scraper/config", response_model=AdminScraperConfig)
async def scraper_config_patch(
    request: Request,
    body: AdminScraperConfigPatch,
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    if body.cron_hour is not None and not (0 <= body.cron_hour <= 23):
        raise HTTPException(status_code=400, detail="cron_hour must be 0-23")
    if body.cron_minute is not None and not (0 <= body.cron_minute <= 59):
        raise HTTPException(status_code=400, detail="cron_minute must be 0-59")
    if body.max_links is not None and body.max_links < 1:
        raise HTTPException(status_code=400, detail="max_links must be >= 1")

    s = await update_scraper_settings(
        seed_urls=body.seed_urls,
        scheduler_enabled=body.scheduler_enabled,
        cron_hour=body.cron_hour,
        cron_minute=body.cron_minute,
        max_links=body.max_links,
    )
    await apply_scheduler_config(request.app)
    return AdminScraperConfig(
        seed_urls=s.seed_urls,
        scheduler_enabled=s.scheduler_enabled,
        cron_hour=s.cron_hour,
        cron_minute=s.cron_minute,
        max_links=s.max_links,
        storage_dir=s.storage_dir,
        api_base_url=s.api_base_url,
    )


def _telegram_stats_from_dict(raw: dict | None) -> AdminTelegramScrapeStats:
    raw = raw or {}
    return AdminTelegramScrapeStats(
        messages_seen=int(raw.get("messages_seen", 0)),
        messages_skipped=int(raw.get("messages_skipped", 0)),
        documents_inserted=int(raw.get("documents_inserted", 0)),
        documents_updated=int(raw.get("documents_updated", 0)),
        errors=int(raw.get("errors", 0)),
        text_posts=int(raw.get("text_posts", 0)),
        pdf_posts=int(raw.get("pdf_posts", 0)),
        pptx_posts=int(raw.get("pptx_posts", 0)),
        image_posts=int(raw.get("image_posts", 0)),
        unsupported=int(raw.get("unsupported", 0)),
    )


def _telegram_run_item(run) -> AdminTelegramRunItem:
    return AdminTelegramRunItem(
        id=str(run.id),
        trigger=run.trigger,
        status=run.status,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        stats=_telegram_stats_from_dict(run.stats if isinstance(run.stats, dict) else None),
        error_message=run.error_message,
    )


@router.post("/admin/telegram/scrape", response_model=AdminJobEnqueued)
async def trigger_telegram_scrape(
    body: TelegramScrapeRequest = TelegramScrapeRequest(),
    current_user: BaUser = Depends(get_current_admin),
):
    """Enqueue a Telegram scrape cycle via Redis Queue and return the job_id immediately.

    Pass ``message_ids`` in the request body to scrape only those specific messages
    instead of running the full time-range scan.
    """
    _require_superadmin(current_user)
    job_id = str(uuid.uuid4())
    publish_progress(job_id, 0, "Queued", "queued")
    mode_label = (
        f"targeted ({len(body.message_ids)} IDs)" if body.message_ids else "full scan"
    )
    scraper_queue.enqueue(
        run_telegram_scrape_job,
        job_id,
        "manual",
        None,
        None,
        None,
        body.message_ids,
        job_id=job_id,
    )
    return AdminJobEnqueued(
        job_id=job_id,
        status="queued",
        message=f"Telegram scrape job enqueued ({mode_label}). Connect to /v1/progress/{job_id} for live progress.",
    )


@router.get("/admin/telegram/config", response_model=AdminTelegramConfig)
async def telegram_config_get(
    request: Request,
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    s = await get_telegram_settings()
    return AdminTelegramConfig(
        channel_username=s.channel_username,
        scrape_since=s.scrape_since.isoformat(),
        max_messages_per_run=s.max_messages_per_run,
        scheduler_enabled=s.scheduler_enabled,
        cron_hour=s.cron_hour,
        cron_minute=s.cron_minute,
        api_configured=s.api_configured,
        session_configured=s.session_configured,
        next_run_time=get_telegram_next_run_time(request.app),
    )


@router.patch("/admin/telegram/config", response_model=AdminTelegramConfig)
async def telegram_config_patch(
    request: Request,
    body: AdminTelegramConfigPatch,
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    from datetime import date as date_type

    scrape_since = None
    if body.scrape_since is not None:
        try:
            scrape_since = date_type.fromisoformat(body.scrape_since[:10])
        except ValueError as e:
            raise HTTPException(status_code=400, detail="scrape_since must be YYYY-MM-DD") from e
    if body.max_messages_per_run is not None and body.max_messages_per_run < 1:
        raise HTTPException(status_code=400, detail="max_messages_per_run must be >= 1")

    s = await update_telegram_settings(
        channel_username=body.channel_username,
        scrape_since=scrape_since,
        max_messages_per_run=body.max_messages_per_run,
        scheduler_enabled=body.scheduler_enabled,
        cron_hour=body.cron_hour,
        cron_minute=body.cron_minute,
    )
    await apply_telegram_scheduler_config(request.app)
    return AdminTelegramConfig(
        channel_username=s.channel_username,
        scrape_since=s.scrape_since.isoformat(),
        max_messages_per_run=s.max_messages_per_run,
        scheduler_enabled=s.scheduler_enabled,
        cron_hour=s.cron_hour,
        cron_minute=s.cron_minute,
        api_configured=s.api_configured,
        session_configured=s.session_configured,
        next_run_time=get_telegram_next_run_time(request.app),
    )


@router.get("/admin/telegram/runs", response_model=AdminTelegramRunList)
async def telegram_runs(
    limit: int = Query(20, ge=1, le=100),
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    runs = await list_telegram_runs(limit=limit)
    return AdminTelegramRunList(runs=[_telegram_run_item(r) for r in runs])


@router.get("/admin/telegram/messages", response_model=AdminTelegramMessageList)
async def telegram_messages(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    channel: str | None = Query(None),
    message_type: str | None = Query(None),
    document_status: str | None = Query(None),
    ingest_filter: str | None = Query(
        None,
        description="indexed | failed | manual | none",
    ),
    search: str | None = Query(None),
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    rows, total = await list_telegram_messages(
        limit=limit,
        offset=offset,
        channel=channel,
        message_type=message_type,
        document_status=document_status,
        ingest_filter=ingest_filter,
        search=search,
    )
    return AdminTelegramMessageList(
        messages=[
            AdminTelegramMessageItem(
                id=str(msg.id),
                channel_username=msg.channel_username,
                message_id=int(msg.message_id),
                content_part=msg.content_part,
                posted_at=msg.posted_at.isoformat(),
                message_type=msg.message_type,
                text_preview=msg.text_preview,
                file_name=msg.file_name,
                mime_type=msg.mime_type,
                byte_size=msg.byte_size,
                telegram_url=msg.telegram_url,
                document_id=str(msg.document_id) if msg.document_id else None,
                document_status=doc_status,
                skip_reason=msg.skip_reason,
            )
            for msg, doc_status in rows
        ],
        total=total,
    )


@router.delete("/admin/telegram/messages/clear", response_model=AdminTelegramClearResult)
async def telegram_messages_clear(
    channel: str | None = Query(None),
    delete_documents: bool = Query(
        True,
        description="Also delete linked documents (and chunks) sourced from Telegram.",
    ),
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    deleted = await clear_telegram_messages(
        channel=channel,
        delete_linked_documents=delete_documents,
    )
    return AdminTelegramClearResult(deleted=deleted)


@router.delete("/admin/telegram/messages/{row_id}")
async def telegram_message_delete(
    row_id: str,
    delete_document: bool = Query(True),
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    try:
        uid = uuid.UUID(row_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid row id") from e
    ok = await delete_telegram_message(uid, delete_linked_document=delete_document)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "ok"}


@router.post("/admin/telegram/messages/{row_id}/reingest")
async def telegram_message_reingest(
    row_id: str,
    force_index: bool = Query(False),
    current_user: BaUser = Depends(get_current_admin),
):
    _require_superadmin(current_user)
    try:
        uid = uuid.UUID(row_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid row id") from e
    try:
        status = await reingest_telegram_message(uid, force_index=force_index)
    except LookupError:
        raise HTTPException(status_code=404, detail="Not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": status}


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
    enforcement_status: str = Query("in_effect", description="'in_effect' or 'draft'"),
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

    try:
        es = EnforcementStatusEnum(enforcement_status)
    except ValueError:
        es = EnforcementStatusEnum.IN_EFFECT

    if existing_doc is not None and overwrite:
        doc = existing_doc
        doc.title = (file.filename or doc.title)[:512]
        doc.uploaded_by_id = current_user.id
        doc.status = DocStatusEnum.PENDING
        doc.processing_stage = None
        doc.ingest_error = None
        doc.enforcement_status = es
        duplicate = True
    else:
        doc = Document(
            id=uuid.uuid4(),
            title=(file.filename or "Untitled")[:512],
            file_hash=file_hash,
            status=DocStatusEnum.PENDING,
            uploaded_by_id=current_user.id,
            enforcement_status=es,
        )
        db.add(doc)
        await db.flush()

    pdf_bytes = await file.read()
    mime_type = _guess_mime(file.filename, file.content_type)
    doc_id = str(doc.id)
    await db.commit()
    await db.refresh(doc)

    # Enqueue ingestion as a background RQ job so the upload request returns immediately.
    job_id = str(uuid.uuid4())
    publish_progress(job_id, 0, "Queued for ingestion", "queued")
    ingest_queue.enqueue(
        run_ingest_job,
        job_id,
        doc_id,
        pdf_bytes,
        mime_type,
        file.filename or "upload",
        job_id=job_id,
    )
    logger.info("upload_queued doc=%s job=%s", doc_id, job_id)

    return DocumentStatus(
        doc_id=doc_id,
        status="pending",
        duplicate=duplicate,
        processing_stage=None,
        ingest_error=None,
        job_id=job_id,
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


# ─── Notification endpoints ───────────────────────────────────────────────────


@router.get("/admin/notifications/config", response_model=AdminNotificationConfig)
async def notification_config_get(
    request: Request,
    current_user: BaUser = Depends(get_current_admin),
):
    """Return current notification configuration (scheduler, recipients, watermark)."""
    _require_superadmin(current_user)
    from apps.api.notification_service import get_notification_settings
    from apps.api.notification_scheduler import get_notification_next_run_time

    s = await get_notification_settings()
    return AdminNotificationConfig(
        scheduler_enabled=s.scheduler_enabled,
        interval_hours=s.interval_hours,
        email_recipients=s.email_recipients,
        sms_recipients=s.sms_recipients,
        min_relevance_score=s.min_relevance_score,
        last_checked_at=s.last_checked_at.isoformat() if s.last_checked_at else None,
        next_run_time=get_notification_next_run_time(request.app),
    )


@router.patch("/admin/notifications/config", response_model=AdminNotificationConfig)
async def notification_config_patch(
    request: Request,
    body: AdminNotificationConfigPatch,
    current_user: BaUser = Depends(get_current_admin),
):
    """Update notification configuration and reschedule the background job."""
    _require_superadmin(current_user)
    from apps.api.notification_service import update_notification_settings
    from apps.api.notification_scheduler import (
        apply_notification_scheduler_config,
        get_notification_next_run_time,
    )

    if body.interval_hours is not None and body.interval_hours < 1:
        raise HTTPException(status_code=400, detail="interval_hours must be >= 1")
    if body.min_relevance_score is not None and not (0.0 <= body.min_relevance_score <= 1.0):
        raise HTTPException(status_code=400, detail="min_relevance_score must be between 0 and 1")

    s = await update_notification_settings(
        scheduler_enabled=body.scheduler_enabled,
        interval_hours=body.interval_hours,
        email_recipients=body.email_recipients,
        sms_recipients=body.sms_recipients,
        min_relevance_score=body.min_relevance_score,
    )
    await apply_notification_scheduler_config(request.app)

    return AdminNotificationConfig(
        scheduler_enabled=s.scheduler_enabled,
        interval_hours=s.interval_hours,
        email_recipients=s.email_recipients,
        sms_recipients=s.sms_recipients,
        min_relevance_score=s.min_relevance_score,
        last_checked_at=s.last_checked_at.isoformat() if s.last_checked_at else None,
        next_run_time=get_notification_next_run_time(request.app),
    )


@router.post("/admin/notifications/trigger", response_model=AdminNotificationTriggerResult)
async def notification_trigger(
    current_user: BaUser = Depends(get_current_admin),
):
    """Manually enqueue a notification check cycle via Redis Queue."""
    _require_superadmin(current_user)
    from apps.api.queue.jobs.notification_job import run_notification_job
    from apps.api.queue.queues import notification_queue

    job_id = str(uuid.uuid4())
    publish_progress(job_id, 0, "Queued", "queued")
    notification_queue.enqueue(
        run_notification_job,
        job_id,
        "manual",
        job_id=job_id,
    )
    return AdminNotificationTriggerResult(
        job_id=job_id,
        status="queued",
        message=(
            "Notification check enqueued. "
            "Connect to /v1/admin/progress/{job_id} for live progress."
        ),
    )


@router.get("/admin/notifications/logs", response_model=AdminNotificationLogList)
async def notification_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: BaUser = Depends(get_current_admin),
):
    """Return recent notification send history (both email and SMS)."""
    _require_superadmin(current_user)
    from apps.api.notification_service import list_notification_logs

    rows, total = await list_notification_logs(limit=limit, offset=offset)
    return AdminNotificationLogList(
        logs=[
            AdminNotificationLogItem(
                id=str(row.id),
                doc_id=str(row.doc_id) if row.doc_id else None,
                doc_title=row.doc_title,
                channel=row.channel,
                recipient=row.recipient,
                subject=row.subject,
                summary=row.summary,
                status=row.status,
                error=row.error,
                trigger=row.trigger,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ],
        total=total,
    )

