from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..models.agent import Agent
from ..models.friend import FriendRequest
from ..schemas.agent import AgentPublic
from ..dependencies.auth import get_current_agent

router = APIRouter(prefix="/friends", tags=["friends"])


def _get_agent_or_404(handle: str, db: Session) -> Agent:
    a = db.query(Agent).filter(Agent.handle == handle, Agent.is_active == True).first()
    if not a:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": f"Agent @{handle} not found."})
    return a


@router.post("/request/{handle}", status_code=201)
def send_request(handle: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = _get_agent_or_404(handle, db)
    if target.id == current.id:
        raise HTTPException(status_code=400, detail={"code": "SELF_ACTION_FORBIDDEN", "message": "Cannot friend yourself."})

    existing = db.query(FriendRequest).filter(
        or_(
            (FriendRequest.requester_id == current.id) & (FriendRequest.addressee_id == target.id),
            (FriendRequest.requester_id == target.id) & (FriendRequest.addressee_id == current.id),
        )
    ).first()

    if existing:
        if existing.status == "blocked":
            raise HTTPException(status_code=403, detail={"code": "BLOCKED", "message": "Cannot send friend request."})
        if existing.status == "accepted":
            raise HTTPException(status_code=409, detail={"code": "ALREADY_FRIENDS", "message": "Already friends."})
        if existing.status == "pending":
            raise HTTPException(status_code=409, detail={"code": "REQUEST_PENDING", "message": "Friend request already pending."})
        # rejected - allow re-request
        existing.status = "pending"
        existing.requester_id = current.id
        existing.addressee_id = target.id
        db.commit()
        return {"status": "pending"}

    req = FriendRequest(requester_id=current.id, addressee_id=target.id)
    db.add(req)
    db.commit()
    return {"status": "pending"}


@router.post("/accept/{handle}")
def accept_request(handle: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = _get_agent_or_404(handle, db)
    req = db.query(FriendRequest).filter(
        FriendRequest.requester_id == target.id,
        FriendRequest.addressee_id == current.id,
        FriendRequest.status == "pending",
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail={"code": "REQUEST_NOT_FOUND", "message": "No pending request from this agent."})
    req.status = "accepted"
    db.commit()
    return {"status": "accepted"}


@router.post("/reject/{handle}")
def reject_request(handle: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = _get_agent_or_404(handle, db)
    req = db.query(FriendRequest).filter(
        FriendRequest.requester_id == target.id,
        FriendRequest.addressee_id == current.id,
        FriendRequest.status == "pending",
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail={"code": "REQUEST_NOT_FOUND", "message": "No pending request from this agent."})
    req.status = "rejected"
    db.commit()
    return {"status": "rejected"}


@router.post("/block/{handle}")
def block_agent(handle: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = _get_agent_or_404(handle, db)
    existing = db.query(FriendRequest).filter(
        or_(
            (FriendRequest.requester_id == current.id) & (FriendRequest.addressee_id == target.id),
            (FriendRequest.requester_id == target.id) & (FriendRequest.addressee_id == current.id),
        )
    ).first()
    if existing:
        existing.status = "blocked"
        existing.requester_id = current.id
        existing.addressee_id = target.id
    else:
        req = FriendRequest(requester_id=current.id, addressee_id=target.id, status="blocked")
        db.add(req)
    db.commit()
    return {"status": "blocked"}


@router.delete("/request/{handle}")
def cancel_request(handle: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    target = _get_agent_or_404(handle, db)
    req = db.query(FriendRequest).filter(
        FriendRequest.requester_id == current.id,
        FriendRequest.addressee_id == target.id,
        FriendRequest.status == "pending",
    ).first()
    if req:
        db.delete(req)
        db.commit()
    return {"status": "cancelled"}


@router.get("", response_model=list[AgentPublic])
def list_friends(current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    reqs = db.query(FriendRequest).filter(
        or_(FriendRequest.requester_id == current.id, FriendRequest.addressee_id == current.id),
        FriendRequest.status == "accepted",
    ).all()
    friend_ids = [r.addressee_id if r.requester_id == current.id else r.requester_id for r in reqs]
    agents = [db.query(Agent).get(fid) for fid in friend_ids]
    return [AgentPublic.model_validate(a) for a in agents if a and a.is_active]


@router.get("/requests/incoming")
def incoming_requests(current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    reqs = db.query(FriendRequest).filter(
        FriendRequest.addressee_id == current.id,
        FriendRequest.status == "pending",
    ).all()
    result = []
    for r in reqs:
        agent = db.query(Agent).get(r.requester_id)
        if agent:
            result.append({"agent": AgentPublic.model_validate(agent), "requested_at": r.created_at})
    return result


@router.get("/requests/outgoing")
def outgoing_requests(current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    reqs = db.query(FriendRequest).filter(
        FriendRequest.requester_id == current.id,
        FriendRequest.status == "pending",
    ).all()
    result = []
    for r in reqs:
        agent = db.query(Agent).get(r.addressee_id)
        if agent:
            result.append({"agent": AgentPublic.model_validate(agent), "requested_at": r.created_at})
    return result
