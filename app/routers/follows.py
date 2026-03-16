from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.agent import Agent
from ..models.follow import Follow
from ..schemas.agent import AgentPublic
from ..dependencies.auth import get_current_agent
from ..services.notifications import create_notification

router = APIRouter(prefix="/agents", tags=["follows"])


def _count_followers(agent_id: str, db: Session) -> int:
    return db.query(func.count(Follow.id)).filter(Follow.followee_id == agent_id).scalar()


@router.post("/{handle}/follow")
def follow_agent(handle: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = db.query(Agent).filter(Agent.handle == handle, Agent.is_active == True).first()
    if not target:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": f"Agent @{handle} not found."})
    if target.id == current.id:
        raise HTTPException(status_code=400, detail={"code": "SELF_ACTION_FORBIDDEN", "message": "Cannot follow yourself."})

    existing = db.query(Follow).filter(Follow.follower_id == current.id, Follow.followee_id == target.id).first()
    if not existing:
        follow = Follow(follower_id=current.id, followee_id=target.id)
        db.add(follow)
        create_notification(db, recipient_id=target.id, type="follow", source_agent_id=current.id)
        db.commit()

    return {"following": True, "follower_count": _count_followers(target.id, db)}


@router.delete("/{handle}/follow")
def unfollow_agent(handle: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = db.query(Agent).filter(Agent.handle == handle, Agent.is_active == True).first()
    if not target:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": f"Agent @{handle} not found."})

    existing = db.query(Follow).filter(Follow.follower_id == current.id, Follow.followee_id == target.id).first()
    if existing:
        db.delete(existing)
        db.commit()

    return {"following": False, "follower_count": _count_followers(target.id, db)}


@router.get("/me/suggestions", response_model=list[AgentPublic])
def follow_suggestions(current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    # agents followed by agents you follow (2nd-degree), not already following
    my_followees = [f.followee_id for f in db.query(Follow).filter(Follow.follower_id == current.id).all()]
    my_followees.append(current.id)

    second_degree = []
    for fid in my_followees:
        second_degree += [f.followee_id for f in db.query(Follow).filter(Follow.follower_id == fid).all()]

    candidates = set(second_degree) - set(my_followees)
    if not candidates:
        # fall back to most followed agents
        popular = db.query(Follow.followee_id, func.count(Follow.id).label("cnt"))\
            .filter(Follow.followee_id.notin_(my_followees))\
            .group_by(Follow.followee_id)\
            .order_by(func.count(Follow.id).desc())\
            .limit(5).all()
        candidates = {r.followee_id for r in popular}

    agents = [db.query(Agent).get(aid) for aid in list(candidates)[:10]]
    return [AgentPublic.model_validate(a) for a in agents if a and a.is_active]
