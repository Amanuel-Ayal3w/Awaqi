import hashlib
import hmac
import logging
import os
import uuid
from typing import List

from ai_engine.hybrid_retrieval import load_chunks_by_ids, retrieve_fused_chunk_ids
from ai_engine.query_nlu import detect_query_language
from ai_engine.rag_answer import answer_from_chunks
from ai_engine.safety import should_refuse_query
from database import get_session
from database.models.customer import CuUser
from database.models.session import (
    Channel,
    ChatSession,
    Feedback,
    FeedbackRating,
    Message,
    MessageRole,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
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
logger = logging.getLogger(__name__)

SESSION_TOKEN_SECRET = os.environ.get("SESSION_TOKEN_SECRET", "")
if not SESSION_TOKEN_SECRET:
    raise RuntimeError(
        "SESSION_TOKEN_SECRET env var is not set. "
        "Add it to your .env file or export it before starting the server."
    )


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


async def _resolve_telegram_customer(
    telegram_chat_id: int, db: AsyncSession
) -> uuid.UUID | None:
    """Look up a cu_user_id for a linked Telegram chat_id, or None if not linked."""
    result = await db.execute(
        select(CuUser.id).where(CuUser.telegram_chat_id == telegram_chat_id)
    )
    row = result.scalar_one_or_none()
    return row


async def _get_or_create_session(
    session_id: str,
    language: str,
    session_token: str | None,
    db: AsyncSession,
    channel: Channel = Channel.WEB,
    cu_user_id: uuid.UUID | None = None,
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
        # Backfill cu_user_id on existing session if the user just linked their account
        if cu_user_id is not None and chat_session.cu_user_id is None:
            chat_session.cu_user_id = cu_user_id
            db.add(chat_session)
        elif chat_session.user_id is None and chat_session.cu_user_id is None:
            _validate_guest_session_token(chat_session, session_token)
        return chat_session

    chat_session = ChatSession(
        id=sid,
        channel=channel,
        language=language,
        cu_user_id=cu_user_id,
    )
    db.add(chat_session)
    await db.flush()
    return chat_session


def _citation_from_storage(d: object) -> Citation | None:
    if not isinstance(d, dict):
        return None
    try:
        return Citation(
            source=str(d.get("source", "source"))[:512],
            page=int(d.get("page", 1)),
            text=str(d.get("text", ""))[:4000],
            document_title=d.get("document_title"),
            proclamation_number=d.get("proclamation_number"),
            article_number=d.get("article_number"),
        )
    except Exception:
        return None


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    session_token: str | None = Header(None, alias="X-Session-Token"),
    x_channel: str | None = Header(None, alias="X-Channel"),
    x_telegram_chat_id: str | None = Header(None, alias="X-Telegram-Chat-Id"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    channel = Channel.TELEGRAM if x_channel == "telegram" else Channel.WEB

    cu_user_id: uuid.UUID | None = None
    if x_telegram_chat_id:
        try:
            cu_user_id = await _resolve_telegram_customer(int(x_telegram_chat_id), db)
        except (ValueError, TypeError):
            pass

    chat_session = await _get_or_create_session(
        request.session_id,
        request.language or "en",
        session_token,
        db,
        channel=channel,
        cu_user_id=cu_user_id,
    )

    user_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.USER,
        content=request.message,
    )
    db.add(user_msg)
    await db.flush()

    refuse, refusal_msg = should_refuse_query(request.message)
    if refuse and refusal_msg:
        logger.info(
            "chat_refused session_id=%s reason=safety",
            chat_session.id,
        )
        assistant_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=refusal_msg,
            cited_chunks=[],
            confidence_score=0.0,
        )
        db.add(assistant_msg)
        return ChatResponse(
            response_text=refusal_msg,
            citations=[],
            confidence_score=0.0,
            session_token=_build_guest_session_token(chat_session.id),
            detected_language=detect_query_language(request.message),
        )

    lang = detect_query_language(request.message)
    logger.info(
        "chat_query_lang=%s session_id=%s",
        lang,
        chat_session.id,
    )

    try:
        fused_ids = await retrieve_fused_chunk_ids(
            db,
            request.message,
            taxpayer_category=request.taxpayer_category,
        )
        chunks = await load_chunks_by_ids(db, fused_ids)
        response_text, citation_dicts, confidence_score = await answer_from_chunks(
            request.message,
            chunks,
            language=request.language or "en",
        )
    except Exception:
        logger.exception("rag_pipeline_error session_id=%s", chat_session.id)
        response_text = (
            "The knowledge base search is temporarily unavailable "
            "(Gemini embeddings may be unavailable — check GOOGLE_API_KEY). "
            "Please try again in a moment."
        )
        citation_dicts = []
        confidence_score = 0.0
    citations = [Citation(**c) for c in citation_dicts]

    assistant_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.ASSISTANT,
        content=response_text,
        cited_chunks=[c.model_dump() for c in citations],
        confidence_score=confidence_score,
    )
    db.add(assistant_msg)

    return ChatResponse(
        response_text=response_text,
        citations=citations,
        confidence_score=confidence_score,
        session_token=_build_guest_session_token(chat_session.id),
        detected_language=lang,
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

    out: list[ChatMessage] = []
    for msg in messages:
        cites: list[Citation] | None = None
        if msg.role == MessageRole.ASSISTANT and msg.cited_chunks:
            parsed = [_citation_from_storage(x) for x in msg.cited_chunks]
            cites = [c for c in parsed if c is not None]
            if not cites:
                cites = None
        out.append(
            ChatMessage(
                role=str(getattr(msg.role, "value", msg.role)),
                content=msg.content,
                timestamp=msg.created_at.isoformat(),
                citations=cites,
            )
        )
    return out


@router.get("/export/{session_id}")
async def export_session_transcript(
    session_id: str,
    session_token: str | None = Header(None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    """Plain-text export of the conversation (AWA-35 partial — transcript only)."""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if chat_session.user_id is None:
        _validate_guest_session_token(chat_session, session_token)

    result = await db.execute(
        select(Message)
        .where(Message.session_id == chat_session.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    lines: list[str] = []
    for msg in messages:
        role = str(getattr(msg.role, "value", msg.role))
        ts = msg.created_at.isoformat()
        lines.append(f"[{ts}] {role.upper()}")
        lines.append(msg.content)
        lines.append("")
    body = "\n".join(lines).strip() + "\n"
    return Response(content=body, media_type="text/plain; charset=utf-8")


@router.post("/feedback/{message_id}")
async def submit_feedback(
    message_id: str,
    request: FeedbackRequest,
    session_token: str | None = Header(None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    try:
        mid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_id must be a valid UUID",
        )

    result = await db.execute(
        select(Message).where(Message.id == mid)
    )
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    session_result = await db.execute(
        select(ChatSession).where(ChatSession.id == message.session_id)
    )
    chat_session = session_result.scalar_one_or_none()
    if chat_session is not None and chat_session.user_id is None:
        _validate_guest_session_token(chat_session, session_token)

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
