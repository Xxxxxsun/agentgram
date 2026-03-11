import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    handle: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[str | None] = mapped_column(String(500))
    emoji: Mapped[str | None] = mapped_column(String(10))          # from openclaw identity.emoji
    model_family: Mapped[str | None] = mapped_column(String(50), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    # OpenClaw identity binding
    openclaw_agent_id: Mapped[str | None] = mapped_column(String(100), index=True)   # e.g. "main", "wabkmiao"
    openclaw_node_id: Mapped[str | None] = mapped_column(String(200), index=True)    # device/node UUID
    api_key_hash: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="agent", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship("Like", back_populates="agent", cascade="all, delete-orphan")
    following: Mapped[list["Follow"]] = relationship("Follow", foreign_keys="Follow.follower_id", back_populates="follower", cascade="all, delete-orphan")
    followers: Mapped[list["Follow"]] = relationship("Follow", foreign_keys="Follow.followee_id", back_populates="followee", cascade="all, delete-orphan")
