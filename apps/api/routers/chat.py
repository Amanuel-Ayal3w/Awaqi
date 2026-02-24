import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Citation,
    FeedbackRequest,
)
from database import get_session
from database.models.session import (
    Channel,
    ChatSession,
    Feedback,
    FeedbackRating,
    Message,
    MessageRole,
)

router = APIRouter()


async def _get_or_create_session(
    session_id: str,
    language: str,
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
    db: AsyncSession = Depends(get_session),
):
    chat_session = await _get_or_create_session(
        request.session_id, request.language or "en", db
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
    )


@router.get("/history/{session_id}", response_model=List[ChatMessage])
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_session),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must be a valid UUID",
        )

    result = await db.execute(
        select(Message)
        .where(Message.session_id == sid)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return [
        ChatMessage(
            role=msg.role,
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
