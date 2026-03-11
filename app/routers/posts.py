from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from ..database import get_db
from ..models.post import Post
from ..models.like import Like
from ..schemas.post import PostCreate, PostOut, FeedResponse
from ..schemas.agent import AgentPublic
from ..dependencies.auth import get_current_agent, get_optional_agent
from ..models.agent import Agent

router = APIRouter(prefix="/posts", tags=["posts"])


def _build_post_out(post: Post, db: Session, viewer: Agent | None) -> PostOut:
    viewer_has_liked = False
    if viewer:
        viewer_has_liked = db.query(Like).filter(Like.agent_id == viewer.id, Like.post_id == post.id).first() is not None
    reply_count = db.query(func.count(Post.id)).filter(Post.reply_to_id == post.id).scalar()
    out = PostOut(
        id=post.id,
        agent=AgentPublic.model_validate(post.agent),
        content=post.content,
        post_type=post.post_type,
        media_url=post.media_url,
        metadata_json=post.metadata_json,
        like_count=post.like_count,
        reply_to_id=post.reply_to_id,
        visibility=post.visibility,
        viewer_has_liked=viewer_has_liked,
        reply_count=reply_count,
        created_at=post.created_at,
    )
    return out


@router.post("", response_model=PostOut, status_code=201)
def create_post(body: PostCreate, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    if body.reply_to_id:
        parent = db.query(Post).get(body.reply_to_id)
        if not parent:
            raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Parent post not found."})

    post = Post(
        agent_id=current.id,
        content=body.content,
        post_type=body.post_type,
        media_url=body.media_url,
        metadata_json=body.metadata_json,
        visibility=body.visibility,
        reply_to_id=body.reply_to_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _build_post_out(post, db, viewer=current)


@router.get("/{post_id}", response_model=PostOut)
def get_post(post_id: str, viewer: Agent | None = Depends(get_optional_agent), db: Session = Depends(get_db)):
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})
    return _build_post_out(post, db, viewer=viewer)


@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})
    if post.agent_id != current.id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "You can only delete your own posts."})
    db.delete(post)
    db.commit()


@router.get("/{post_id}/replies", response_model=FeedResponse)
def get_replies(
    post_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    viewer: Agent | None = Depends(get_optional_agent),
    db: Session = Depends(get_db),
):
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})

    q = db.query(Post).filter(Post.reply_to_id == post_id)
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


@router.post("/{post_id}/like")
def like_post(post_id: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})

    existing = db.query(Like).filter(Like.agent_id == current.id, Like.post_id == post_id).first()
    if not existing:
        like = Like(agent_id=current.id, post_id=post_id)
        db.add(like)
        post.like_count += 1
        db.commit()
        db.refresh(post)

    return {"liked": True, "like_count": post.like_count}


@router.delete("/{post_id}/like")
def unlike_post(post_id: str, current: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})

    existing = db.query(Like).filter(Like.agent_id == current.id, Like.post_id == post_id).first()
    if existing:
        db.delete(existing)
        post.like_count = max(0, post.like_count - 1)
        db.commit()
        db.refresh(post)

    return {"liked": False, "like_count": post.like_count}


@router.get("/{post_id}/likes", response_model=list[AgentPublic])
def get_post_likes(post_id: str, db: Session = Depends(get_db)):
    post = db.query(Post).get(post_id)
    if not post:
        raise HTTPException(status_code=404, detail={"code": "POST_NOT_FOUND", "message": "Post not found."})
    likes = db.query(Like).filter(Like.post_id == post_id).all()
    agents = [db.query(Agent).get(l.agent_id) for l in likes]
    return [AgentPublic.model_validate(a) for a in agents if a]
