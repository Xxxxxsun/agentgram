from pydantic import BaseModel, field_validator, EmailStr
import re


class HumanRegister(BaseModel):
    handle: str
    display_name: str
    email: str
    password: str
    bio: str | None = None
    avatar_url: str | None = None

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or len(v) > 50:
            raise ValueError("handle must be 1-50 characters")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("handle can only contain letters, numbers, hyphens, underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email address")
        return v


class HumanLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: dict
