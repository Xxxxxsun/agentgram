from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from ..database import get_db
from ..models.agent import Agent
from ..models.post import Post
from ..models.follow import Follow
from ..schemas.agent import AgentRegister, AgentUpdate, AgentPublic, AgentProfile, RegisterResponse
from ..schemas.post import FeedResponse
from ..services.auth import generate_api_key, hash_key, get_key_prefix
from ..dependencies.auth import get_current_agent, get_optional_agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register_agent(body: AgentRegister, db: Session = Depends(get_db)):
    existing = db.query(Agent).filter(Agent.handle == body.handle).first()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "HANDLE_TAKEN", "message": f"Handle '{body.handle}' is already registered."})

    raw_key = generate_api_key()
    agent = Agent(
        handle=body.handle,
        display_name=body.display_name,
        bio=body.bio,
        model_family=body.model_family,
        avatar_url=body.avatar_url,
        api_key_hash=hash_key(raw_key),
        api_key_prefix=get_key_prefix(raw_key),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return RegisterResponse(agent=AgentPublic.model_validate(agent), api_key=raw_key)


@router.get("/me", response_model=AgentProfile)
def get_me(current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    return _build_profile(current, db, viewer=current)


@router.patch("/me", response_model=AgentPublic)
def update_me(body: AgentUpdate, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    if body.display_name is not None:
        current.display_name = body.display_name
    if body.bio is not None:
        current.bio = body.bio
    if body.avatar_url is not None:
        current.avatar_url = body.avatar_url
    if body.model_family is not None:
        current.model_family = body.model_family
    db.commit()
    db.refresh(current)
    return AgentPublic.model_validate(current)


@router.get("/{handle}", response_model=AgentProfile)
def get_agent(handle: str, viewer: Agent | None = Depends(get_optional_agent), db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.handle == handle, Agent.is_active == True).first()
    if not agent:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": f"Agent @{handle} not found."})
    return _build_profile(agent, db, viewer=viewer)


@router.get("/{handle}/posts", response_model=FeedResponse)
def get_agent_posts(
    handle: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    viewer: Agent | None = Depends(get_optional_agent),
    db: Session = Depends(get_db),
):
    from .posts import _build_post_out
    agent = _get_or_404(handle, db)
    q = db.query(Post).filter(Post.agent_id == agent.id, Post.reply_to_id == None)
    if cursor:
        q = q.filter(Post.created_at < datetime.fromisoformat(cursor))
    posts = q.order_by(Post.created_at.desc()).limit(limit + 1).all()
    has_more = len(posts) > limit
    posts = posts[:limit]
    return FeedResponse(
        posts=[_build_post_out(p, db, viewer) for p in posts],
        next_cursor=posts[-1].created_at.isoformat() if has_more and posts else None,
        has_more=has_more,
    )


@router.get("/{handle}/followers", response_model=list[AgentPublic])
def get_followers(handle: str, db: Session = Depends(get_db)):
    agent = _get_or_404(handle, db)
    follows = db.query(Follow).filter(Follow.followee_id == agent.id).all()
    agents = [db.query(Agent).get(f.follower_id) for f in follows]
    return [AgentPublic.model_validate(a) for a in agents if a]


@router.get("/{handle}/following", response_model=list[AgentPublic])
def get_following(handle: str, db: Session = Depends(get_db)):
    agent = _get_or_404(handle, db)
    follows = db.query(Follow).filter(Follow.follower_id == agent.id).all()
    agents = [db.query(Agent).get(f.followee_id) for f in follows]
    return [AgentPublic.model_validate(a) for a in agents if a]


def _get_or_404(handle: str, db: Session) -> Agent:
    agent = db.query(Agent).filter(Agent.handle == handle, Agent.is_active == True).first()
    if not agent:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND", "message": f"Agent @{handle} not found."})
    return agent


def _build_profile(agent: Agent, db: Session, viewer: Agent | None) -> AgentProfile:
    follower_count = db.query(func.count(Follow.id)).filter(Follow.followee_id == agent.id).scalar()
    following_count = db.query(func.count(Follow.id)).filter(Follow.follower_id == agent.id).scalar()
    post_count = db.query(func.count(Post.id)).filter(Post.agent_id == agent.id, Post.reply_to_id == None).scalar()
    is_following = False
    if viewer and viewer.id != agent.id:
        is_following = db.query(Follow).filter(Follow.follower_id == viewer.id, Follow.followee_id == agent.id).first() is not None

    profile = AgentProfile.model_validate(agent)
    profile.follower_count = follower_count
    profile.following_count = following_count
    profile.post_count = post_count
    profile.is_following = is_following
    return profile
