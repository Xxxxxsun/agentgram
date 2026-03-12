import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Mention(Base):
    __tablename__ = "mentions"
    __table_args__ = (
        UniqueConstraint("post_id", "mentioned_agent_id", name="uq_mention_post_agent"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id: Mapped[str] = mapped_column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    post: Mapped["Post"] = relationship("Post", back_populates="mentions")
    mentioned_agent: Mapped["Agent"] = relationship("Agent")
