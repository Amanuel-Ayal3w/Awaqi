"""
Telegram ↔ Web account linking endpoints.

Flow:
  1. Telegram user sends /link to the bot.
  2. Bot calls POST /v1/auth/telegram/link-request  {chat_id: 12345}
     → API stores  tg:link:{token} → chat_id  in Redis for 10 min
     → Returns     {token, link_url}
  3. Bot DMs the user a link:  https://<web>/link-telegram?token=<token>
  4. User opens the link in a browser, logs in (if needed), and clicks "Connect".
  5. Web app calls POST /v1/auth/telegram/link-confirm  {token: "<token>"}
     with the customer's Bearer auth token.
     → API resolves token → chat_id, sets cu_user.telegram_chat_id = chat_id
     → Deletes the one-time token from Redis
  6. From now on every Telegram message includes X-Telegram-Chat-Id: 12345,
     and the chat endpoint looks up the cu_user_id and links chat sessions.

Unlink: DELETE /v1/auth/telegram/link  (authenticated customer, clears the column)
"""

import logging
import os
import secrets

import httpx
import redis.asyncio as aioredis
from database import get_session
from database.models.customer import CuUser
from database.redis_client import get_redis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_customer

logger = logging.getLogger(__name__)
router = APIRouter()

_LINK_TOKEN_TTL = 600  # 10 minutes
_WEB_BASE_URL = os.environ.get("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


async def _notify_telegram(chat_id: int, display_name: str) -> None:
    """Send a confirmation message to the Telegram user after linking."""
    if not _BOT_TOKEN:
        return
    name = display_name.replace(".", "\\.").replace("-", "\\-").replace("_", "\\_").replace("!", "\\!")
    text = f" Linked\\! You are now signed in as *{name}*\\.\n\nYour Telegram conversations will sync with your Awaqi web account\\."
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"},
            )
    except Exception:
        logger.warning("tg_notify_failed chat_id=%s", chat_id)


def _link_key(token: str) -> str:
    return f"tg:link:{token}"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LinkRequestBody(BaseModel):
    chat_id: int


class LinkRequestResponse(BaseModel):
    token: str
    link_url: str
    expires_in_seconds: int


class LinkConfirmBody(BaseModel):
    token: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/link-request",
    response_model=LinkRequestResponse,
    summary="Generate a one-time link token for Telegram → web account linking",
)
async def link_request(
    body: LinkRequestBody,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Called by the Telegram bot (no user auth required — the bot authenticates
    using a shared secret header instead; see TELEGRAM_BOT_SECRET).

    Stores  tg:link:{token} = "{chat_id}"  with a 10-minute TTL.
    Returns the token and a URL the user should open in their browser.
    """
    token = secrets.token_urlsafe(32)
    await redis.setex(_link_key(token), _LINK_TOKEN_TTL, str(body.chat_id))
    link_url = f"{_WEB_BASE_URL}/link-telegram?token={token}"
    logger.info("tg_link_request chat_id=%s token=%s", body.chat_id, token[:8] + "…")
    return LinkRequestResponse(
        token=token,
        link_url=link_url,
        expires_in_seconds=_LINK_TOKEN_TTL,
    )


@router.post(
    "/link-confirm",
    summary="Confirm a Telegram link (requires customer auth)",
    status_code=status.HTTP_200_OK,
)
async def link_confirm(
    body: LinkConfirmBody,
    customer: CuUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Called by the web frontend after the user clicks "Connect Telegram".
    Requires a valid customer session (Bearer token or cookie).

    Resolves the one-time token → Telegram chat_id, then sets
    cu_user.telegram_chat_id = chat_id and deletes the token.
    """
    raw = await redis.get(_link_key(body.token))
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link token is invalid or has expired. Please use /link again in Telegram.",
        )

    chat_id = int(raw)

    # Make sure no other account already owns this chat_id
    existing = await db.execute(
        select(CuUser).where(CuUser.telegram_chat_id == chat_id)
    )
    other = existing.scalar_one_or_none()
    if other is not None and other.id != customer.id:
        await redis.delete(_link_key(body.token))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Telegram account is already linked to a different Awaqi account.",
        )

    customer.telegram_chat_id = chat_id
    db.add(customer)
    await redis.delete(_link_key(body.token))

    logger.info("tg_link_confirmed cu_user_id=%s chat_id=%s", customer.id, chat_id)

    display_name = customer.name or customer.email
    await _notify_telegram(chat_id, display_name)

    return {"status": "ok", "telegram_chat_id": chat_id, "display_name": display_name}


@router.delete(
    "/link",
    summary="Unlink Telegram account (requires customer auth)",
    status_code=status.HTTP_200_OK,
)
async def unlink(
    customer: CuUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_session),
):
    """Remove the Telegram → web account association."""
    if customer.telegram_chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Telegram account is currently linked.",
        )
    old_id = customer.telegram_chat_id
    customer.telegram_chat_id = None
    db.add(customer)
    logger.info("tg_link_removed cu_user_id=%s old_chat_id=%s", customer.id, old_id)
    return {"status": "ok"}


@router.get(
    "/link",
    summary="Get linked Telegram status (requires customer auth)",
)
async def get_link_status(
    customer: CuUser = Depends(get_current_customer),
):
    """Return whether the customer has a linked Telegram account."""
    return {
        "linked": customer.telegram_chat_id is not None,
        "telegram_chat_id": customer.telegram_chat_id,
    }
