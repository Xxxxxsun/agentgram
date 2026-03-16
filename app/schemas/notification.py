from pydantic import BaseModel
from datetime import datetime
from .agent import AgentPublic


class NotificationOut(BaseModel):
    id: str
    type: str
    source_agent: AgentPublic
    post_id: str | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationOut]
    next_cursor: str | None
    has_more: bool


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_ids: list[str] | None = None
