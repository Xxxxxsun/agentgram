from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.agent import Agent
from ..services.auth import verify_key, get_key_prefix
from ..services.jwt import decode_token


def _agent_from_api_key(x_api_key: str, db: Session) -> Agent | None:
    if not x_api_key or not x_api_key.startswith("sk_ag_"):
        return None
    prefix = get_key_prefix(x_api_key)
    agent = db.query(Agent).filter(
        Agent.api_key_prefix == prefix,
        Agent.account_type == "agent",
        Agent.is_active == True,
    ).first()
    if agent and verify_key(x_api_key, agent.api_key_hash):
        return agent
    return None


def _agent_from_jwt(authorization: str, db: Session) -> Agent | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    user_id = decode_token(token)
    if not user_id:
        return None
    return db.query(Agent).filter(Agent.id == user_id, Agent.is_active == True).first()


def get_current_agent(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Agent:
    account = _agent_from_api_key(x_api_key, db) if x_api_key else None
    if not account:
        account = _agent_from_jwt(authorization, db) if authorization else None
    if not account:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid or missing credentials."})
    return account


def get_optional_agent(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Agent | None:
    account = _agent_from_api_key(x_api_key, db) if x_api_key else None
    if not account:
        account = _agent_from_jwt(authorization, db) if authorization else None
    return account
