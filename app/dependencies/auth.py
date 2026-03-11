from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.agent import Agent
from ..services.auth import verify_key, get_key_prefix


def get_current_agent(
    x_api_key: str = Header(..., description="Agent API key: sk_ag_..."),
    db: Session = Depends(get_db),
) -> Agent:
    if not x_api_key.startswith("sk_ag_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")
    prefix = get_key_prefix(x_api_key)
    agent = db.query(Agent).filter(Agent.api_key_prefix == prefix, Agent.is_active == True).first()
    if not agent or not verify_key(x_api_key, agent.api_key_hash):
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    return agent


def get_optional_agent(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Agent | None:
    if not x_api_key:
        return None
    try:
        return get_current_agent(x_api_key, db)
    except HTTPException:
        return None
