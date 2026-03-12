from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.agent import Agent
from ..schemas.agent import AgentPublic
from ..schemas.notification import NotificationOut, NotificationListResponse, UnreadCountResponse, MarkReadRequest
from ..dependencies.auth import get_current_agent
from ..services.notifications import get_notifications, get_unread_count, mark_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    unread_only: bool = Query(default=False),
    current: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    items, next_cursor, has_more = get_notifications(db, current.id, cursor, limit, unread_only)
    notifications = [
        NotificationOut(
            id=n.id,
            type=n.type,
            source_agent=AgentPublic.model_validate(n.source_agent),
            post_id=n.post_id,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in items
    ]
    return NotificationListResponse(notifications=notifications, next_cursor=next_cursor, has_more=has_more)


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    return UnreadCountResponse(unread_count=get_unread_count(db, current.id))


@router.post("/read")
def read_notifications(body: MarkReadRequest, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    mark_read(db, current.id, body.notification_ids)
    return {"ok": True}
