import hashlib
import hmac
import json
import logging
import os
import uuid
from typing import List

from ai_engine.agent.react_agent import (
    AgentResult,
    run_awaqi_max,
    run_awaqi_max_stream,
    trace_to_json,
)
from ai_engine.hybrid_retrieval import load_chunks_by_ids, retrieve_fused_chunk_ids
from ai_engine.query_nlu import detect_query_language
from ai_engine.rag_answer import answer_from_chunks, answer_from_chunks_stream
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
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps_rate_limit import require_rate_limit
from apps.api.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSessionItem,
    ChatSessionList,
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

    agent_trace_payload: list[dict] | None = None
    web_citations_payload: list[dict] | None = None

    try:
        if request.mode == "awaqi_max":
            agent_result = await run_awaqi_max(
                db,
                request.message,
                language=request.language or "en",
                taxpayer_category=request.taxpayer_category,
                retrieval_mode="optimized",
            )
            response_text = agent_result.answer
            citation_dicts = agent_result.citations
            confidence_score = agent_result.confidence
            follow_up_suggestions = []
            agent_trace_payload = trace_to_json(agent_result.trace)
            web_citations_payload = agent_result.web_citations or None
        else:
            fused_ids = await retrieve_fused_chunk_ids(
                db,
                request.message,
                taxpayer_category=request.taxpayer_category,
            )
            chunks = await load_chunks_by_ids(db, fused_ids)
            response_text, citation_dicts, confidence_score, follow_up_suggestions = (
                await answer_from_chunks(
                    request.message,
                    chunks,
                    language=request.language or "en",
                )
            )
    except Exception as e:
        logger.exception(
            "rag_pipeline_error session_id=%s exception=%s", chat_session.id, repr(e)
        )
        # A failed SELECT/DB call in retrieval leaves the transaction aborted.
        # Roll back before attempting to persist fallback assistant output.
        await db.rollback()
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
        response_text = (
            "The knowledge base search is temporarily unavailable "
            "(Gemini embeddings may be unavailable — check GOOGLE_API_KEY). "
            "Please try again in a moment."
        )
        citation_dicts = []
        confidence_score = 0.0
        follow_up_suggestions = []
   
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
        follow_up_suggestions=follow_up_suggestions,
        mode=request.mode,
        agent_trace=agent_trace_payload,
        web_citations=web_citations_payload,
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    session_token: str | None = Header(None, alias="X-Session-Token"),
    x_channel: str | None = Header(None, alias="X-Channel"),
    x_telegram_chat_id: str | None = Header(None, alias="X-Telegram-Chat-Id"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    """
    SSE streaming endpoint. Emits events:
      {"type": "status",  "text": "..."}          — tool-call progress (max mode)
      {"type": "delta",   "text": "..."}          — text chunk
      {"type": "done",    "response_text": "...", "citations": [...],
                          "confidence_score": 0.8, "session_token": "...",
                          "detected_language": "am", "follow_up_suggestions": [...],
                          "mode": "basic"}        — final event
      {"type": "error",   "detail": "..."}        — on failure
    """
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

    lang = detect_query_language(request.message)
    session_tok = _build_guest_session_token(chat_session.id)

    refuse, refusal_msg = should_refuse_query(request.message)
    if refuse and refusal_msg:
        assistant_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=refusal_msg,
            cited_chunks=[],
            confidence_score=0.0,
        )
        db.add(assistant_msg)

        async def _refuse_gen():
            yield _sse({"type": "delta", "text": refusal_msg})
            yield _sse({
                "type": "done",
                "response_text": refusal_msg,
                "citations": [],
                "confidence_score": 0.0,
                "session_token": session_tok,
                "detected_language": lang,
                "follow_up_suggestions": [],
                "mode": request.mode,
            })

        return StreamingResponse(_refuse_gen(), media_type="text/event-stream")

    # Capture mutable state from the async generator
    state: dict = {}

    async def _generate():
        try:
            if request.mode == "awaqi_max":
                async for item in run_awaqi_max_stream(
                    db,
                    request.message,
                    language=request.language or "en",
                    taxpayer_category=request.taxpayer_category,
                    retrieval_mode="optimized",
                ):
                    if isinstance(item, AgentResult):
                        state["result"] = item
                    elif isinstance(item, tuple) and item[0] == "status":
                        yield _sse({"type": "status", "text": item[1]})
                    elif isinstance(item, str):
                        yield _sse({"type": "delta", "text": item})
            else:
                fused_ids = await retrieve_fused_chunk_ids(
                    db,
                    request.message,
                    taxpayer_category=request.taxpayer_category,
                )
                chunks = await load_chunks_by_ids(db, fused_ids)

                async for item in answer_from_chunks_stream(
                    request.message,
                    chunks,
                    language=request.language or "en",
                ):
                    if isinstance(item, str):
                        yield _sse({"type": "delta", "text": item})
                    else:
                        full_text, citation_dicts, confidence_score, follow_ups = item
                        from apps.api.schemas import Citation as CitationSchema
                        citations = [
                            CitationSchema(**c).model_dump()
                            for c in citation_dicts
                        ]
                        state["basic_result"] = (
                            full_text, citations, confidence_score, follow_ups
                        )

        except Exception as exc:
            logger.exception(
                "stream_pipeline_error session_id=%s exception=%s",
                chat_session.id,
                repr(exc),
            )
            yield _sse({"type": "error", "detail": "Generation failed. Please retry."})
            return

        # Finalise: persist assistant message and emit done event
        try:
            if request.mode == "awaqi_max" and "result" in state:
                agent_result: AgentResult = state["result"]
                response_text = agent_result.answer
                citation_dicts = agent_result.citations
                confidence_score = agent_result.confidence
                follow_ups = []
                from apps.api.schemas import Citation as CitationSchema
                citations_ser = [
                    CitationSchema(**c).model_dump()
                    for c in citation_dicts
                ]
                agent_trace = trace_to_json(agent_result.trace)
                web_citations = agent_result.web_citations or None
            elif "basic_result" in state:
                response_text, citations_ser, confidence_score, follow_ups = state["basic_result"]
                agent_trace = None
                web_citations = None
            else:
                response_text = ""
                citations_ser = []
                confidence_score = 0.0
                follow_ups = []
                agent_trace = None
                web_citations = None

            assistant_msg = Message(
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=response_text,
                cited_chunks=citations_ser,
                confidence_score=confidence_score,
            )
            db.add(assistant_msg)

            done_payload: dict = {
                "type": "done",
                "response_text": response_text,
                "citations": citations_ser,
                "confidence_score": confidence_score,
                "session_token": session_tok,
                "detected_language": lang,
                "follow_up_suggestions": follow_ups,
                "mode": request.mode,
            }
            if agent_trace is not None:
                done_payload["agent_trace"] = agent_trace
            if web_citations is not None:
                done_payload["web_citations"] = web_citations

            yield _sse(done_payload)

        except Exception:
            logger.exception("stream_persist_error session_id=%s", chat_session.id)
            yield _sse({"type": "error", "detail": "Failed to persist response."})

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
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


@router.get("/sessions", response_model=ChatSessionList)
async def list_sessions(
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    """Return all sessions for the authenticated customer user (AWA-35)."""

    # Inline session resolution — reuse the apiClient bearer token

    # We need to resolve the logged-in customer from the Authorization header.
    # Delegating to a shared helper keeps the implementation thin.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use the /sessions/me endpoint after authenticating via customer auth.",
    )


@router.get("/sessions/me", response_model=ChatSessionList)
async def list_my_sessions(
    cu_user_id: str | None = None,
    x_cu_user_id: str | None = Header(None, alias="X-Cu-User-Id"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    """
    Return sessions belonging to the authenticated customer (AWA-35).
    The frontend passes the customer UUID in the ``X-Cu-User-Id`` header after
    resolving it from the Better Auth customer session on the client side.
    """
    uid_str = x_cu_user_id or cu_user_id
    if not uid_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Cu-User-Id header required",
        )
    try:
        uid = uuid.UUID(uid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Cu-User-Id must be a valid UUID",
        )

    sessions_result = await db.execute(
        select(ChatSession)
        .where(ChatSession.cu_user_id == uid)
        .order_by(ChatSession.created_at.desc())
        .limit(50)
    )
    sessions = sessions_result.scalars().all()

    items: list[ChatSessionItem] = []
    for s in sessions:
        # Count messages in this session
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.session_id == s.id)
        )
        msg_count = count_result.scalar_one_or_none() or 0

        # Last message timestamp
        last_result = await db.execute(
            select(Message.created_at)
            .where(Message.session_id == s.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_ts = last_result.scalar_one_or_none()

        items.append(
            ChatSessionItem(
                id=str(s.id),
                title=s.title if hasattr(s, "title") and s.title else None,
                created_at=s.created_at.isoformat(),
                message_count=msg_count,
                last_message_at=last_ts.isoformat() if last_ts else None,
            )
        )

    return ChatSessionList(sessions=items)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    x_cu_user_id: str | None = Header(None, alias="X-Cu-User-Id"),
    session_token: str | None = Header(None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    """Delete a chat session and all its messages (AWA-35)."""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Authorisation: either the owning cu_user or a valid guest token
    if x_cu_user_id:
        try:
            uid = uuid.UUID(x_cu_user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Cu-User-Id")
        if chat_session.cu_user_id != uid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    elif chat_session.cu_user_id is None:
        _validate_guest_session_token(chat_session, session_token)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    await db.execute(
        select(Message).where(Message.session_id == sid)  # type: ignore[arg-type]
    )
    # Delete messages first (FK), then the session
    from sqlalchemy import delete as sa_delete
    await db.execute(sa_delete(Message).where(Message.session_id == sid))
    await db.delete(chat_session)


@router.post("/migrate/{session_id}", status_code=status.HTTP_200_OK)
async def migrate_guest_session(
    session_id: str,
    x_cu_user_id: str | None = Header(None, alias="X-Cu-User-Id"),
    session_token: str | None = Header(None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_session),
    _rl: None = Depends(require_rate_limit),
):
    """
    Link an existing guest session to a now-authenticated customer (AWA-34).
    Call this right after the user logs in, passing both the guest session token
    and the newly-resolved X-Cu-User-Id.
    """
    if not x_cu_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Cu-User-Id header required",
        )
    try:
        sid = uuid.UUID(session_id)
        uid = uuid.UUID(x_cu_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id and X-Cu-User-Id must be valid UUIDs",
        )

    result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
    chat_session = result.scalar_one_or_none()
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    _validate_guest_session_token(chat_session, session_token)

    if chat_session.cu_user_id is not None and chat_session.cu_user_id != uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session already belongs to a different user",
        )

    chat_session.cu_user_id = uid
    db.add(chat_session)
    return {"status": "migrated", "session_id": session_id}
