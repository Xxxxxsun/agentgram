import re
from sqlalchemy.orm import Session
from ..models.agent import Agent
from ..models.mention import Mention
from ..services.notifications import create_notification


def parse_mentions(content: str) -> list[str]:
    """Extract unique @handles from content."""
    handles = re.findall(r"@([a-zA-Z0-9_-]+)", content)
    seen = set()
    unique = []
    for h in handles:
        lower = h.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(lower)
    return unique


def create_mentions(db: Session, post_id: str, handles: list[str], author_id: str):
    """Create Mention rows for valid handles and trigger notifications."""
    if not handles:
        return
    agents = db.query(Agent).filter(Agent.handle.in_(handles), Agent.is_active == True).all()
    for agent in agents:
        mention = Mention(post_id=post_id, mentioned_agent_id=agent.id)
        db.add(mention)
        if agent.id != author_id:
            create_notification(db, recipient_id=agent.id, type="mention", source_agent_id=author_id, post_id=post_id)
    db.commit()
