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


class AdminDocumentPatch(BaseModel):
    """Superadmin: re-attribute document to an admin user (or system if null)."""

    uploaded_by_id: Optional[str] = None


class AdminDocumentList(BaseModel):
    documents: List[AdminDocumentItem]


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
