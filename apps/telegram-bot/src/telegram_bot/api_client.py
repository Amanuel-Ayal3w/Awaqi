"""
HTTP client for the Awaqi FastAPI backend.

Calls POST /v1/chat/send and returns a structured ChatResponse dataclass.
Each Telegram user's chat_id is forwarded as X-Forwarded-For: telegram:{chat_id}
so the API's Redis rate limiter gives each user an independent bucket
(requires TRUST_X_FORWARDED_FOR=true + TRUSTED_PROXIES=127.0.0.1 on the API side).
"""

import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

API_BASE_URL = os.environ.get("TELEGRAM_API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = float(os.environ.get("TELEGRAM_API_TIMEOUT", "15"))


@dataclass
class Citation:
    source: str
    page: int
    text: str
    document_title: Optional[str] = None
    proclamation_number: Optional[str] = None
    article_number: Optional[str] = None


@dataclass
class ChatResult:
    response_text: str
    citations: list[Citation]
    confidence_score: float
    session_token: Optional[str]
    detected_language: Optional[str]


class AwagiAPIError(Exception):
    """Raised when the API returns a non-2xx response."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


async def send_message(
    *,
    message: str,
    session_id: str,
    session_token: Optional[str],
    language: str = "en",
    taxpayer_category: Optional[str] = None,
    telegram_chat_id: int,
) -> ChatResult:
    """Send a user message to the FastAPI backend and return the response."""
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Channel": "telegram",
        "X-Forwarded-For": f"telegram:{telegram_chat_id}",
    }
    if session_token:
        headers["X-Session-Token"] = session_token

    payload: dict = {
        "message": message,
        "session_id": session_id,
        "language": language,
    }
    if taxpayer_category:
        payload["taxpayer_category"] = taxpayer_category

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{API_BASE_URL}/v1/chat/send",
            json=payload,
            headers=headers,
        )

    if resp.status_code == 429:
        detail = resp.json().get("detail", {})
        retry = detail.get("retry_after_seconds", 60) if isinstance(detail, dict) else 60
        raise AwagiAPIError(429, f"Rate limit exceeded. Try again in {retry} seconds.")

    if not resp.is_success:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise AwagiAPIError(resp.status_code, str(detail))

    data = resp.json()
    citations = [
        Citation(
            source=c.get("source", ""),
            page=c.get("page", 1),
            text=c.get("text", ""),
            document_title=c.get("document_title"),
            proclamation_number=c.get("proclamation_number"),
            article_number=c.get("article_number"),
        )
        for c in data.get("citations", [])
    ]

    return ChatResult(
        response_text=data["response_text"],
        citations=citations,
        confidence_score=data.get("confidence_score", 0.0),
        session_token=data.get("session_token"),
        detected_language=data.get("detected_language"),
    )
