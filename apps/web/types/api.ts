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
}

export interface AdminDocumentList {
    documents: AdminDocumentItem[];
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
