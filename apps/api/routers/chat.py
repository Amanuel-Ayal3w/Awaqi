import hashlib
import hmac
import os
import uuid
from typing import List

from database import get_session
from database.models.session import (
    Channel,
    ChatSession,
    Feedback,
    FeedbackRating,
    Message,
    MessageRole,
)
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps_rate_limit import require_rate_limit
from apps.api.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Citation,
    FeedbackRequest,
)

router = APIRouter()
SESSION_TOKEN_SECRET = os.getenv("SESSION_TOKEN_SECRET", "dev-session-token-secret-change-me")


def _build_guest_session_token(session_id: uuid.UUID) -> str:
    return hmac.new(
        SESSION_TOKEN_SECRET.encode("utf-8"),
        str(session_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _validate_guest_session_token(
    chat_session: ChatSession, session_token: str | None
) -> None:
    expected = _build_guest_session_token(chat_session.id)
    if not session_token or not hmac.compare_digest(session_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token",
        )


async def _get_or_create_session(
    session_id: str,
    language: str,
    session_token: str | None,
    db: AsyncSession,
) -> ChatSession:
    """Find an existing ChatSession or create a new one for guest users."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must be a valid UUID",
        )

    result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
    chat_session = result.scalar_one_or_none()

    if chat_session is not None:
        if chat_session.user_id is None:
            _validate_guest_session_token(chat_session, session_token)
        return chat_session

    if chat_session is None:
        chat_session = ChatSession(
            id=sid,
            channel=Channel.WEB,
            language=language,
        )
        db.add(chat_session)
        await db.flush()

    return chat_session


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    session_token: str | None = Header(None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    chat_session = await _get_or_create_session(
        request.session_id,
        request.language or "en",
        session_token,
        db,
    )

    # Persist the user message
    user_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.USER,
        content=request.message,
    )
    db.add(user_msg)
    await db.flush()

    # TODO: replace with real ai-engine RAG call once ai-engine is wired up
    # from ai_engine import rag_pipeline
    # rag_result = await rag_pipeline.answer(request.message, language=request.language)
    response_text = (
        "This is a placeholder response. Connect the ai-engine RAG pipeline here."
    )
    citations: list[Citation] = []
    confidence_score = 0.0

    # Persist the assistant message
    assistant_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.ASSISTANT,
        content=response_text,
        cited_chunks=[
            {"source": c.source, "page": c.page, "text": c.text} for c in citations
        ],
        confidence_score=confidence_score,
    )
    db.add(assistant_msg)

    return ChatResponse(
        response_text=response_text,
        citations=citations,
        confidence_score=confidence_score,
        session_token=_build_guest_session_token(chat_session.id),
    )


@router.get("/history/{session_id}", response_model=List[ChatMessage])
async def get_history(
    session_id: str,
    session_token: str | None = Header(None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must be a valid UUID",
        )

    session_result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
    chat_session = session_result.scalar_one_or_none()
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if chat_session.user_id is None:
        _validate_guest_session_token(chat_session, session_token)

    result = await db.execute(
        select(Message)
        .where(Message.session_id == chat_session.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return [
        ChatMessage(
            role=str(getattr(msg.role, "value", msg.role)),
            content=msg.content,
            timestamp=msg.created_at.isoformat(),
        )
        for msg in messages
    ]


@router.post("/feedback/{message_id}")
async def submit_feedback(
    message_id: str,
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        mid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_id must be a valid UUID",
        )

    # Verify the message exists
    result = await db.execute(select(Message).where(Message.id == mid))
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Upsert feedback (unique per message)
    existing = await db.execute(
        select(Feedback).where(Feedback.message_id == mid)
    )
    feedback = existing.scalar_one_or_none()

    rating = FeedbackRating.THUMBS_UP if request.score > 0 else FeedbackRating.THUMBS_DOWN

    if feedback:
        feedback.rating = rating
        feedback.comment = request.comment
    else:
        feedback = Feedback(
            message_id=mid,
            rating=rating,
            comment=request.comment,
        )
        db.add(feedback)

    return {"status": "ok", "message_id": message_id}
