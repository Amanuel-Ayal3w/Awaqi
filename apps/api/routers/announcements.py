"""User-facing announcements router.

Exposes the in-app notification feed for the customer portal.
Authenticated customer users poll these endpoints to populate the
notification bell in the chat layout header.
"""

from __future__ import annotations

from datetime import datetime, timezone

from database.models.customer import CuUser
from fastapi import APIRouter, Depends, Query

from apps.api.deps import get_current_customer

router = APIRouter()


@router.get("/announcements")
async def list_announcements(
    limit: int = Query(20, ge=1, le=100),
    since: str | None = Query(
        None,
        description="ISO-8601 datetime. When provided, only return announcements after this timestamp.",
    ),
    _user: CuUser = Depends(get_current_customer),
):
    """Return recent tax announcements for the in-app notification feed."""
    from apps.api.notification_service import list_announcements as _list

    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            since_dt = None

    items = await _list(limit=limit, since=since_dt)
    return {
        "announcements": [
            {
                "id": str(item.id),
                "doc_id": str(item.doc_id) if item.doc_id else None,
                "doc_title": item.doc_title,
                "summary": item.summary,
                "source_url": item.source_url,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
        "total": len(items),
    }


@router.get("/announcements/unread-count")
async def unread_count(
    since: str = Query(
        ...,
        description="ISO-8601 datetime of the last time the user opened the notification panel.",
    ),
    _user: CuUser = Depends(get_current_customer),
):
    """Return count of announcements created after ``since`` for the unread badge."""
    from apps.api.notification_service import count_announcements_since

    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        since_dt = datetime.now(timezone.utc)

    count = await count_announcements_since(since_dt)
    return {"unread_count": count}
