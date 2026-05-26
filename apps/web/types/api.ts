/**
 * TypeScript mirrors of apps/api/schemas.py Pydantic models.
 * Keep in sync whenever the FastAPI schemas change.
 */

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatRequest {
    message: string;
    session_id: string;
    language?: string;
    /** Optional bias for retrieval query embedding (e.g. business vs individual). */
    taxpayer_category?: string | null;
}

export interface Citation {
    source: string;
    page: number;
    text: string;
    document_title?: string | null;
    proclamation_number?: string | null;
    article_number?: string | null;
}

export interface ChatResponse {
    response_text: string;
    citations: Citation[];
    confidence_score: number;
    session_token?: string;
    /** Server-side query language hint (Amharic / English / mixed). */
    detected_language?: string | null;
}

export interface ChatMessage {
    role: "user" | "assistant" | "system";
    content: string;
    timestamp: string;
    citations?: Citation[] | null;
}

export interface FeedbackRequest {
    score: number;
    comment?: string;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface DocumentStatus {
    doc_id: string;
    status: string;
    duplicate?: boolean;
    processing_stage?: string | null;
    ingest_error?: string | null;
}

export interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
}

export interface LogEntryList {
    logs: LogEntry[];
}

export interface AdminDocumentItem {
    id: string;
    title: string;
    status: string;
    source_url?: string | null;
    created_at: string;
    processing_stage?: string | null;
    ingest_error?: string | null;
    byte_size?: number | null;
    uploaded_by_id?: string | null;
    uploaded_by_email?: string | null;
    uploaded_by_name?: string | null;
}

export interface AdminDocumentDetail extends AdminDocumentItem {
    file_hash?: string | null;
    registry_key?: string | null;
    storage_path?: string | null;
}

export interface ExtractedPagePreview {
    page_number: number;
    text: string;
    extraction_mode: string;
    ocr_mean_confidence?: number | null;
}

export interface AdminDocumentContentPreview {
    doc_id: string;
    title: string;
    status: string;
    ingest_error?: string | null;
    source_url?: string | null;
    storage_path?: string | null;
    has_stored_pdf: boolean;
    text_source: string;
    pages: ExtractedPagePreview[];
    full_text: string;
    chunk_count: number;
    requires_manual_review: boolean;
    review_reason?: string | null;
    mean_ocr_confidence?: number | null;
    text_quality_warning?: boolean;
    text_quality_reasons?: string[];
    tesseract_langs_installed?: string[];
    ocr_langs_configured?: string;
    ocr_langs_resolved?: string;
}

export interface AdminDocumentList {
    documents: AdminDocumentItem[];
    total: number;
}

export interface AdminScrapeStats {
    discovered: number;
    inserted: number;
    skipped: number;
    errors: number;
}

export interface AdminScrapeResult {
    status: string;
    stats: AdminScrapeStats;
}

export interface AdminScraperRunItem {
    id: string;
    trigger: string;
    status: string;
    started_at: string;
    finished_at?: string | null;
    stats?: AdminScrapeStats | null;
    error_message?: string | null;
}

export interface AdminScraperRunList {
    runs: AdminScraperRunItem[];
}

export interface AdminScraperConfig {
    seed_urls: string[];
    scheduler_enabled: boolean;
    cron_hour: number;
    cron_minute: number;
    max_links: number;
    storage_dir: string;
    api_base_url: string;
}

export interface AdminScraperConfigPatch {
    seed_urls?: string[];
    scheduler_enabled?: boolean;
    cron_hour?: number;
    cron_minute?: number;
    max_links?: number;
}

export interface AdminScraperStatus {
    scheduler_enabled: boolean;
    cron_hour: number;
    cron_minute: number;
    timezone: string;
    next_run_time?: string | null;
    last_run?: AdminScraperRunItem | null;
}

export interface AdminTelegramScrapeStats {
    messages_seen: number;
    messages_skipped: number;
    documents_inserted: number;
    documents_updated: number;
    errors: number;
    text_posts: number;
    pdf_posts: number;
    pptx_posts: number;
    image_posts: number;
    unsupported: number;
}

export interface AdminTelegramScrapeResult {
    status: string;
    stats: AdminTelegramScrapeStats;
}

export interface AdminTelegramRunItem {
    id: string;
    trigger: string;
    status: string;
    started_at: string;
    finished_at?: string | null;
    stats?: AdminTelegramScrapeStats | null;
    error_message?: string | null;
}

export interface AdminTelegramRunList {
    runs: AdminTelegramRunItem[];
}

export interface AdminTelegramConfig {
    channel_username: string;
    scrape_since: string;
    max_messages_per_run: number;
    scheduler_enabled: boolean;
    cron_hour: number;
    cron_minute: number;
    api_configured: boolean;
    session_configured: boolean;
}

export interface AdminTelegramConfigPatch {
    channel_username?: string;
    scrape_since?: string;
    max_messages_per_run?: number;
    scheduler_enabled?: boolean;
    cron_hour?: number;
    cron_minute?: number;
}

export interface AdminTelegramMessageItem {
    id: string;
    channel_username: string;
    message_id: number;
    posted_at: string;
    message_type: string;
    text_preview?: string | null;
    file_name?: string | null;
    mime_type?: string | null;
    byte_size?: number | null;
    telegram_url?: string | null;
    document_id?: string | null;
    document_status?: string | null;
    skip_reason?: string | null;
}

export interface AdminTelegramMessageList {
    messages: AdminTelegramMessageItem[];
    total: number;
}

export interface DocumentStatusCount {
    status: string;
    count: number;
}

export interface AdminAnalytics {
    documents_total: number;
    documents_by_status: DocumentStatusCount[];
    chunks_total: number;
    admin_users_total: number;
    customer_users_total: number;
    chat_sessions_total: number;
    messages_total: number;
    messages_last_7_days: number;
}

export interface AdminSystemHealth {
    database_ok: boolean;
    redis_ok: boolean;
    redis_latency_ms?: number | null;
}

export interface AdminUserItem {
    id: string;
    name?: string | null;
    email: string;
    role: string;
    is_active: boolean;
    created_at: string;
}

export interface AdminUserList {
    users: AdminUserItem[];
}
