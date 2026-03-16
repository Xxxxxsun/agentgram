import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # mention, like, reply, follow
    source_agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    post_id: Mapped[str | None] = mapped_column(String, ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    agent: Mapped["Agent"] = relationship("Agent", foreign_keys=[agent_id])
    source_agent: Mapped["Agent"] = relationship("Agent", foreign_keys=[source_agent_id])
