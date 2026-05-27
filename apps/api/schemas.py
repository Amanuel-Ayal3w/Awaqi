from typing import List, Optional

from pydantic import BaseModel


# Chat Models
class ChatRequest(BaseModel):
    message: str
    session_id: str
    language: Optional[str] = "en"
    taxpayer_category: Optional[str] = None


class Citation(BaseModel):
    source: str
    page: int
    text: str
    document_title: Optional[str] = None
    proclamation_number: Optional[str] = None
    article_number: Optional[str] = None


class ChatResponse(BaseModel):
    response_text: str
    citations: List[Citation]
    confidence_score: float
    session_token: Optional[str] = None
    detected_language: Optional[str] = None
    follow_up_suggestions: List[str] = []


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
    source_url: Optional[str] = None
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


class AdminDocumentList(BaseModel):
    documents: List[AdminDocumentItem]
    total: int


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
