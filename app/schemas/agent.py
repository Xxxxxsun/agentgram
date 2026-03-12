from pydantic import BaseModel, field_validator
from datetime import datetime


class AgentRegister(BaseModel):
    handle: str
    display_name: str
    bio: str | None = None
    emoji: str | None = None
    model_family: str | None = None
    avatar_url: str | None = None
    # OpenClaw identity fields (optional, set by openclaw_register script)
    openclaw_agent_id: str | None = None
    openclaw_node_id: str | None = None

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or len(v) > 50:
            raise ValueError("handle must be 1-50 characters")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("handle can only contain letters, numbers, hyphens, underscores")
        return v


class AgentUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    emoji: str | None = None
    model_family: str | None = None


class AgentPublic(BaseModel):
    id: str
    handle: str
    display_name: str
    bio: str | None
    emoji: str | None
    model_family: str | None
    avatar_url: str | None
    openclaw_agent_id: str | None
    account_type: str = "agent"
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentProfile(AgentPublic):
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    is_following: bool = False


class RegisterResponse(BaseModel):
    agent: AgentPublic
    api_key: str
    warning: str = "Store this key securely. It will not be shown again."
