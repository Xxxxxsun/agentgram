from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from ..models.notification import Notification


def create_notification(
    db: Session,
    recipient_id: str,
    type: str,
    source_agent_id: str,
    post_id: str | None = None,
):
    """Create a notification. Skips self-notifications and duplicates."""
    if recipient_id == source_agent_id:
        return
    # Check for duplicate (same type + source + post)
    q = db.query(Notification).filter(
        Notification.agent_id == recipient_id,
        Notification.type == type,
        Notification.source_agent_id == source_agent_id,
    )
    if post_id:
        q = q.filter(Notification.post_id == post_id)
    if q.first():
        return
    notif = Notification(
        agent_id=recipient_id,
        type=type,
        source_agent_id=source_agent_id,
        post_id=post_id,
    )
    db.add(notif)


def get_notifications(
    db: Session,
    agent_id: str,
    cursor: str | None = None,
    limit: int = 20,
    unread_only: bool = False,
) -> tuple[list[Notification], str | None, bool]:
    q = db.query(Notification).filter(Notification.agent_id == agent_id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    if cursor:
        cursor_dt = datetime.fromisoformat(cursor)
        q = q.filter(Notification.created_at < cursor_dt)
    items = q.order_by(Notification.created_at.desc()).limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = items[-1].created_at.isoformat() if has_more and items else None
    return items, next_cursor, has_more


def get_unread_count(db: Session, agent_id: str) -> int:
    return db.query(func.count(Notification.id)).filter(
        Notification.agent_id == agent_id,
        Notification.is_read == False,
    ).scalar()


def mark_read(db: Session, agent_id: str, notification_ids: list[str] | None = None):
    q = db.query(Notification).filter(Notification.agent_id == agent_id, Notification.is_read == False)
    if notification_ids:
        q = q.filter(Notification.id.in_(notification_ids))
    q.update({Notification.is_read: True}, synchronize_session="fetch")
    db.commit()
