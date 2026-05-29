from typing import Any, List, Literal, Optional

from pydantic import BaseModel

AssistantMode = Literal["basic", "awaqi_max"]


# Chat Models
class ChatRequest(BaseModel):
    message: str
    session_id: str
    language: Optional[str] = "en"
    taxpayer_category: Optional[str] = None
    # ``basic`` = single-shot RAG (default); ``awaqi_max`` = ReAct agent with
    # iterative KB search + Ethiopian-grounded web search.
    mode: AssistantMode = "basic"


class Citation(BaseModel):
    source: str
    page: int
    text: str
    document_title: Optional[str] = None
    proclamation_number: Optional[str] = None
    article_number: Optional[str] = None
    enforcement_status: str = "in_effect"
    source_url: Optional[str] = None


class ChatResponse(BaseModel):
    response_text: str
    citations: List[Citation]
    confidence_score: float
    session_token: Optional[str] = None
    detected_language: Optional[str] = None
    follow_up_suggestions: List[str] = []
    mode: AssistantMode = "basic"
    # Populated only when ``mode == "awaqi_max"`` — list of {step, type, tool_name, …}.
    agent_trace: Optional[List[dict[str, Any]]] = None
    web_citations: Optional[List[dict[str, Any]]] = None


class ChatSessionItem(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: str
    message_count: int = 0
    last_message_at: Optional[str] = None


class ChatSessionList(BaseModel):
    sessions: List[ChatSessionItem]


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str
    citations: Optional[List[Citation]] = None

class FeedbackRequest(BaseModel):
    score: int
    comment: Optional[str] = None

# Admin Models
class DocumentStatus(BaseModel):
    doc_id: str
    status: str
    duplicate: bool = False
    processing_stage: Optional[str] = None
    ingest_error: Optional[str] = None
    job_id: Optional[str] = None

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

class LogEntryList(BaseModel):
    logs: List[LogEntry]


class AdminDocumentItem(BaseModel):
    id: str
    title: str
    status: str
    enforcement_status: str = "in_effect"
    source_url: Optional[str] = None
    source_system: Optional[str] = None
    storage_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: str
    processing_stage: Optional[str] = None
    ingest_error: Optional[str] = None
    byte_size: Optional[int] = None
    uploaded_by_id: Optional[str] = None
    uploaded_by_email: Optional[str] = None
    uploaded_by_name: Optional[str] = None


class AdminDocumentDetail(AdminDocumentItem):
    file_hash: Optional[str] = None
    registry_key: Optional[str] = None
    storage_path: Optional[str] = None


class ExtractedPagePreview(BaseModel):
    page_number: int
    text: str
    extraction_mode: str
    ocr_mean_confidence: Optional[float] = None


class AdminDocumentContentPreview(BaseModel):
    doc_id: str
    title: str
    status: str
    ingest_error: Optional[str] = None
    source_url: Optional[str] = None
    storage_path: Optional[str] = None
    has_stored_pdf: bool
    text_source: str
    pages: List[ExtractedPagePreview]
    full_text: str
    chunk_count: int
    requires_manual_review: bool
    review_reason: Optional[str] = None
    mean_ocr_confidence: Optional[float] = None
    text_quality_warning: bool = False
    text_quality_reasons: List[str] = []
    tesseract_langs_installed: List[str] = []
    ocr_langs_configured: str = "eng+amh"
    ocr_langs_resolved: str = "eng"


class AdminDocumentPatch(BaseModel):
    """Superadmin: re-attribute document to an admin user (or system if null)."""

    uploaded_by_id: Optional[str] = None
    enforcement_status: Optional[str] = None


class AdminDocumentList(BaseModel):
    documents: List[AdminDocumentItem]
    total: int


class AdminDocumentDeleteResult(BaseModel):
    status: str
    deleted_doc_id: str
    deleted_chunks: int = 0


class AdminUserPatch(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentStatusCount(BaseModel):
    status: str
    count: int


class AdminAnalytics(BaseModel):
    documents_total: int
    documents_by_status: List[DocumentStatusCount]
    chunks_total: int
    admin_users_total: int
    customer_users_total: int
    chat_sessions_total: int
    messages_total: int
    messages_last_7_days: int


class AdminSystemHealth(BaseModel):
    """Live dependency checks for admin ops (AWA-40 partial)."""

    database_ok: bool
    redis_ok: bool
    redis_latency_ms: Optional[float] = None


class AdminVectorStoreStats(BaseModel):
    """pgvector inventory for admin vector-store settings."""

    configured_dimension: int
    embedding_model: str
    column_dimension: Optional[int] = None
    chunks_total: int
    chunks_with_embedding: int
    chunks_without_embedding: int
    storage_bytes: int
    stored_dimensions: dict[int, int] = {}
    dimension_mismatch: bool = False


class AdminVectorStoreActionResult(BaseModel):
    action: str
    affected_rows: int
    message: str


class AdminUserItem(BaseModel):
    id: str
    name: Optional[str] = None
    email: str
    role: str
    is_active: bool
    created_at: str


class AdminUserList(BaseModel):
    users: List[AdminUserItem]


class AdminScrapeStats(BaseModel):
    discovered: int = 0
    inserted: int = 0
    skipped: int = 0
    errors: int = 0


class AdminScrapeResult(BaseModel):
    status: str
    stats: AdminScrapeStats


class AdminScraperRunItem(BaseModel):
    id: str
    trigger: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    stats: Optional[AdminScrapeStats] = None
    error_message: Optional[str] = None


class AdminScraperRunList(BaseModel):
    runs: List[AdminScraperRunItem]


class AdminScraperConfig(BaseModel):
    seed_urls: List[str]
    scheduler_enabled: bool
    cron_hour: int
    cron_minute: int
    max_links: int
    storage_dir: str
    api_base_url: str


class AdminScraperConfigPatch(BaseModel):
    seed_urls: Optional[List[str]] = None
    scheduler_enabled: Optional[bool] = None
    cron_hour: Optional[int] = None
    cron_minute: Optional[int] = None
    max_links: Optional[int] = None


class AdminScraperStatus(BaseModel):
    scheduler_enabled: bool
    cron_hour: int
    cron_minute: int
    timezone: str
    next_run_time: Optional[str] = None
    last_run: Optional[AdminScraperRunItem] = None


class AdminScrapeTriggerRequest(BaseModel):
    """Optional source-selection payload for POST /admin/scrape."""
    sources: Optional[List[str]] = None


class AdminTelegramScrapeStats(BaseModel):
    messages_seen: int = 0
    messages_skipped: int = 0
    documents_inserted: int = 0
    documents_updated: int = 0
    errors: int = 0
    text_posts: int = 0
    pdf_posts: int = 0
    pptx_posts: int = 0
    image_posts: int = 0
    unsupported: int = 0


class AdminTelegramScrapeResult(BaseModel):
    status: str
    stats: AdminTelegramScrapeStats


class AdminTelegramRunItem(BaseModel):
    id: str
    trigger: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    stats: Optional[AdminTelegramScrapeStats] = None
    error_message: Optional[str] = None


class AdminTelegramRunList(BaseModel):
    runs: List[AdminTelegramRunItem]


class AdminTelegramConfig(BaseModel):
    channel_username: str
    scrape_since: str
    max_messages_per_run: int
    scheduler_enabled: bool
    cron_hour: int
    cron_minute: int
    api_configured: bool
    session_configured: bool
    next_run_time: Optional[str] = None


class AdminTelegramConfigPatch(BaseModel):
    channel_username: Optional[str] = None
    scrape_since: Optional[str] = None
    max_messages_per_run: Optional[int] = None
    scheduler_enabled: Optional[bool] = None
    cron_hour: Optional[int] = None
    cron_minute: Optional[int] = None


class AdminTelegramClearResult(BaseModel):
    deleted: int


class AdminJobEnqueued(BaseModel):
    """Returned immediately when a long-running job is queued via RQ."""
    job_id: str
    status: str = "queued"
    message: str = ""


class TelegramScrapeRequest(BaseModel):
    """Optional body for POST /admin/telegram/scrape."""
    message_ids: Optional[List[int]] = None
    """
    When provided, scrape only these specific Telegram message IDs instead of
    running the full time-range scan. Useful for re-ingesting or cherry-picking
    individual posts.
    """


class AdminTelegramMessageItem(BaseModel):
    id: str
    channel_username: str
    message_id: int
    content_part: str
    posted_at: str
    message_type: str
    text_preview: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    byte_size: Optional[int] = None
    telegram_url: Optional[str] = None
    document_id: Optional[str] = None
    document_status: Optional[str] = None
    skip_reason: Optional[str] = None


class AdminTelegramMessageList(BaseModel):
    messages: List[AdminTelegramMessageItem]
    total: int


# ─── Notification ──────────────────────────────────────────────────────────────


class AdminNotificationConfig(BaseModel):
    scheduler_enabled: bool
    interval_hours: int
    email_recipients: List[str]
    sms_recipients: List[str]
    min_relevance_score: float
    last_checked_at: Optional[str] = None
    next_run_time: Optional[str] = None


class AdminNotificationConfigPatch(BaseModel):
    scheduler_enabled: Optional[bool] = None
    interval_hours: Optional[int] = None
    email_recipients: Optional[List[str]] = None
    sms_recipients: Optional[List[str]] = None
    min_relevance_score: Optional[float] = None


class AdminNotificationTriggerResult(BaseModel):
    job_id: str
    status: str
    message: str


class AdminNotificationLogItem(BaseModel):
    id: str
    doc_id: Optional[str] = None
    doc_title: Optional[str] = None
    channel: str
    recipient: str
    subject: Optional[str] = None
    summary: Optional[str] = None
    status: str
    error: Optional[str] = None
    trigger: str
    created_at: str


class AdminNotificationLogList(BaseModel):
    logs: List[AdminNotificationLogItem]
    total: int


class AdminNotificationRunStats(BaseModel):
    docs_checked: int = 0
    docs_relevant: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    sms_sent: int = 0
    sms_failed: int = 0
