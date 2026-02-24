"""
FastAPI shared dependencies.

get_current_admin validates an incoming Better Auth session token by doing
a single JOIN query against the shared PostgreSQL database — no JWT library,
no shared secrets needed.
"""

from datetime import datetime, timezone
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager
from database import get_session
from database.models.auth import BaSession, BaUser


async def get_current_admin(
    authorization: str = Header(..., description="Bearer <better-auth-session-token>"),
    db: AsyncSession = Depends(get_session),
) -> BaUser:
    """
    Validate a Better Auth session token and return the authenticated BaUser.

    The frontend attaches the token from authClient.getSession().session.token
    as 'Authorization: Bearer <token>'. We verify it by looking it up in the
    ba_session table and checking expiry + is_active.

    Raises HTTP 401 if the token is missing, expired, or the user is inactive.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer scheme",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token",
        )

    result = await db.execute(
        select(BaSession)
        .join(BaUser, BaSession.user_id == BaUser.id)
        .where(BaSession.token == token)
        .where(BaSession.expires_at > datetime.now(timezone.utc))
        .options(contains_eager(BaSession.user))
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )

    if not record.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )

    return record.user
