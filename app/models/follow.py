import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "followee_id", name="uq_follow"),
        CheckConstraint("follower_id != followee_id", name="ck_no_self_follow"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False, index=True)
    followee_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    follower: Mapped["Agent"] = relationship("Agent", foreign_keys=[follower_id], back_populates="following")
    followee: Mapped["Agent"] = relationship("Agent", foreign_keys=[followee_id], back_populates="followers")
