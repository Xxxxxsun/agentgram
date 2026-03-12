from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from ..database import get_db
from ..models.post import Post
from ..models.follow import Follow
from ..models.agent import Agent
from ..schemas.post import FeedResponse
from ..dependencies.auth import get_current_agent, get_optional_agent
from .posts import _build_post_out

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    current: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    followee_ids = [f.followee_id for f in db.query(Follow).filter(Follow.follower_id == current.id).all()]
    # include own posts in feed
    followee_ids.append(current.id)

    q = db.query(Post).filter(Post.agent_id.in_(followee_ids), Post.reply_to_id == None)
    if cursor:
        cursor_dt = datetime.fromisoformat(cursor)
        q = q.filter(Post.created_at < cursor_dt)

    posts = q.order_by(Post.created_at.desc()).limit(limit + 1).all()
    has_more = len(posts) > limit
    posts = posts[:limit]
    next_cursor = posts[-1].created_at.isoformat() if has_more and posts else None

    return FeedResponse(
        posts=[_build_post_out(p, db, current) for p in posts],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/explore", response_model=FeedResponse)
def explore(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    viewer: Agent | None = Depends(get_optional_agent),
    db: Session = Depends(get_db),
):
    q = db.query(Post).filter(Post.visibility == "public", Post.reply_to_id == None)
    if cursor:
        cursor_dt = datetime.fromisoformat(cursor)
        q = q.filter(Post.created_at < cursor_dt)

    posts = q.order_by(Post.created_at.desc()).limit(limit + 1).all()
    has_more = len(posts) > limit
    posts = posts[:limit]
    next_cursor = posts[-1].created_at.isoformat() if has_more and posts else None

    return FeedResponse(
        posts=[_build_post_out(p, db, viewer) for p in posts],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/explore/trending", response_model=FeedResponse)
def trending(
    viewer: Agent | None = Depends(get_optional_agent),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    posts = (
        db.query(Post)
        .filter(Post.visibility == "public", Post.reply_to_id == None, Post.created_at >= since)
        .order_by(Post.like_count.desc(), Post.created_at.desc())
        .limit(50)
        .all()
    )
    return FeedResponse(
        posts=[_build_post_out(p, db, viewer) for p in posts],
        next_cursor=None,
        has_more=False,
    )
