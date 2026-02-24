
from fastapi import APIRouter, File, UploadFile

from apps.api.schemas import (
    DocumentStatus,
    LogEntry,
    LogEntryList,
    LoginRequest,
    ScraperStatus,
    Token,
)

router = APIRouter()

@router.post("/auth/login", response_model=Token)
async def login(request: LoginRequest):
    return Token(access_token="working_token", token_type="bearer")

@router.post("/admin/upload", response_model=DocumentStatus)
async def upload_document(file: UploadFile = File(...)):
    return DocumentStatus(doc_id="working_id", status="uploaded")

@router.get("/admin/logs", response_model=LogEntryList)
async def get_logs():
    return LogEntryList(logs=[
        LogEntry(timestamp="2024-01-01T00:00:00Z", level="INFO", message="working"),
        LogEntry(timestamp="2024-01-01T00:01:00Z", level="INFO", message="working")
    ])

@router.post("/admin/scrape", response_model=ScraperStatus)
async def trigger_scrape():
    return ScraperStatus(job_id="working_job", status="started")
