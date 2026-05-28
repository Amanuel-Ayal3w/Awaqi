"""Server-Sent Events endpoint for real-time job progress streaming.

Clients connect to ``GET /v1/admin/progress/{job_id}`` and receive a stream of
JSON-encoded progress events until the job reaches ``done`` or ``failed``.

Event format (text/event-stream):
    data: {"job_id": "...", "pct": 42, "step": "Processing item 3/10", "status": "running"}
    data: {"job_id": "...", "pct": 100, "step": "Done", "status": "done"}

A heartbeat comment (`: keep-alive`) is emitted every ~5 s when no updates arrive.

Auth: ``EventSource`` sends cookies automatically, so the standard
``get_current_admin`` dep (which accepts cookie tokens) works without changes.
Alternatively, pass ``?token=<session_token>`` as a query parameter.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from database import get_session
from database.models.auth import BaSession, BaUser
from database.redis_client import get_redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

logger = logging.getLogger(__name__)

router = APIRouter()

_HEARTBEAT_INTERVAL = 5  # seconds between keep-alive comments
_MAX_POLL_WAIT = 0.5     # seconds per get_message poll tick


async def _get_admin_for_sse(
    request: Request,
    token: Optional[str] = Query(None, description="Session token (for EventSource)"),
    db: AsyncSession = Depends(get_session),
) -> BaUser:
    """Accept token from Authorization header, cookie, OR ?token= query param."""
    from apps.api.deps import _extract_bearer_or_cookie_token

    raw = _extract_bearer_or_cookie_token(
        authorization=request.headers.get("authorization"),
        request=request,
        cookie_names=("better-auth.session_token", "__Secure-better-auth.session_token"),
    )
    resolved_token = raw or token
    if not resolved_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")

    result = await db.execute(
        select(BaSession)
        .join(BaUser, BaSession.user_id == BaUser.id)
        .where(BaSession.token == resolved_token)
        .where(BaSession.expires_at > datetime.now(timezone.utc))
        .options(contains_eager(BaSession.user))
    )
    record = result.scalar_one_or_none()
    if record is None or not record.user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token")
    return record.user


@router.get(
    "/progress/{job_id}",
    summary="Stream job progress via Server-Sent Events",
    response_class=StreamingResponse,
)
async def stream_job_progress(
    job_id: str,
    _user: BaUser = Depends(_get_admin_for_sse),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Subscribe to live progress updates for a background job.

    Returns ``text/event-stream``. Each event is a JSON object:
    ``{ job_id, pct, step, status }``.

    The stream closes automatically once ``status`` is ``done`` or ``failed``.
    """

    async def _generate():
        # ── 1. Send the current snapshot immediately so late subscribers see state ──
        current: dict = await redis.hgetall(f"job:{job_id}")
        if current:
            snapshot = {
                "job_id": job_id,
                "pct": int(current.get("pct", 0)),
                "step": current.get("step", ""),
                "status": current.get("status", "unknown"),
            }
            yield f"data: {json.dumps(snapshot)}\n\n"
            if snapshot["status"] in ("done", "failed"):
                return
        else:
            yield f"data: {json.dumps({'job_id': job_id, 'pct': 0, 'step': 'Queued', 'status': 'queued'})}\n\n"

        # ── 2. Subscribe and stream live updates ──
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"progress:{job_id}")
        last_heartbeat = asyncio.get_event_loop().time()

        try:
            while True:
                now = asyncio.get_event_loop().time()

                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=_MAX_POLL_WAIT,
                )

                if msg and msg["type"] == "message":
                    yield f"data: {msg['data']}\n\n"
                    try:
                        data = json.loads(msg["data"])
                        if data.get("status") in ("done", "failed"):
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass
                    last_heartbeat = now
                elif now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                    # Also re-read the hash to catch jobs that finished before
                    # the pub/sub subscription was established.
                    snap = await redis.hgetall(f"job:{job_id}")
                    if snap and snap.get("status") in ("done", "failed"):
                        payload = {
                            "job_id": job_id,
                            "pct": int(snap.get("pct", 100)),
                            "step": snap.get("step", ""),
                            "status": snap.get("status", "done"),
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        break
                    yield ": keep-alive\n\n"
                    last_heartbeat = now
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await pubsub.unsubscribe(f"progress:{job_id}")
                await pubsub.aclose()
            except Exception:
                pass

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
