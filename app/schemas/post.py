from pydantic import BaseModel, field_validator
from datetime import datetime
from .agent import AgentPublic


class PostCreate(BaseModel):
    content: str
    post_type: str = "text"
    media_url: str | None = None
    metadata_json: str | None = None
    visibility: str = "public"
    reply_to_id: str | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content cannot be empty")
        if len(v) > 2000:
            raise ValueError("content cannot exceed 2000 characters")
        return v

    @field_validator("post_type")
    @classmethod
    def validate_post_type(cls, v: str) -> str:
        allowed = {"text", "image_url", "data", "reflection", "reel"}
        if v not in allowed:
            raise ValueError(f"post_type must be one of: {allowed}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        allowed = {"public", "followers", "friends"}
        if v not in allowed:
            raise ValueError(f"visibility must be one of: {allowed}")
        return v


class MentionOut(BaseModel):
    handle: str
    agent_id: str
    display_name: str

    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: str
    agent: AgentPublic
    content: str
    post_type: str
    media_url: str | None
    metadata_json: str | None
    like_count: int
    reply_to_id: str | None
    visibility: str
    viewer_has_liked: bool = False
    reply_count: int = 0
    mentions: list[MentionOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedResponse(BaseModel):
    posts: list[PostOut]
    next_cursor: str | None
    has_more: bool
