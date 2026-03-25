from typing import List, Optional

from pydantic import BaseModel


# Chat Models
class ChatRequest(BaseModel):
    message: str
    session_id: str
    language: Optional[str] = "en"

class Citation(BaseModel):
    source: str
    page: int
    text: str

class ChatResponse(BaseModel):
    response_text: str
    citations: List[Citation]
    confidence_score: float
    session_token: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class FeedbackRequest(BaseModel):
    score: int
    comment: Optional[str] = None

# Admin Models
class DocumentStatus(BaseModel):
    doc_id: str
    status: str

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


class AdminDocumentList(BaseModel):
    documents: List[AdminDocumentItem]


class AdminUserItem(BaseModel):
    id: str
    name: Optional[str] = None
    email: str
    role: str
    is_active: bool
    created_at: str


class AdminUserList(BaseModel):
    users: List[AdminUserItem]
