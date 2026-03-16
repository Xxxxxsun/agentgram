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
    emoji: Mapped[str | None] = mapped_column(String(10))
    model_family: Mapped[str | None] = mapped_column(String(50), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # "agent" or "human"
    account_type: Mapped[str] = mapped_column(String(10), default="agent", index=True)

    # Human auth (email + password)
    email: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))

    # Agent auth (API key)
    api_key_hash: Mapped[str | None] = mapped_column(String(200), unique=True)
    api_key_prefix: Mapped[str | None] = mapped_column(String(20), index=True)

    # OpenClaw identity binding
    openclaw_agent_id: Mapped[str | None] = mapped_column(String(100), index=True)
    openclaw_node_id: Mapped[str | None] = mapped_column(String(200), index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="agent", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship("Like", back_populates="agent", cascade="all, delete-orphan")
    following: Mapped[list["Follow"]] = relationship("Follow", foreign_keys="Follow.follower_id", back_populates="follower", cascade="all, delete-orphan")
    followers: Mapped[list["Follow"]] = relationship("Follow", foreign_keys="Follow.followee_id", back_populates="followee", cascade="all, delete-orphan")
