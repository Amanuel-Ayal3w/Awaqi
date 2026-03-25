/**
 * TypeScript mirrors of apps/api/schemas.py Pydantic models.
 * Keep in sync whenever the FastAPI schemas change.
 */

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatRequest {
    message: string;
    session_id: string;
    language?: string;
}

export interface Citation {
    source: string;
    page: number;
    text: string;
}

export interface ChatResponse {
    response_text: string;
    citations: Citation[];
    confidence_score: number;
    session_token?: string;
}

export interface ChatMessage {
    role: "user" | "assistant" | "system";
    content: string;
    timestamp: string;
}

export interface FeedbackRequest {
    score: number;
    comment?: string;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface DocumentStatus {
    doc_id: string;
    status: string;
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
}

export interface AdminDocumentList {
    documents: AdminDocumentItem[];
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
