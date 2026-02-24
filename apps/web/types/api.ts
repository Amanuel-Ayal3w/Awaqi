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

export interface ScraperStatus {
    job_id: string;
    status: string;
}
