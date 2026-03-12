from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, text

from .database import engine, Base, SessionLocal
from .models import Agent, Post, Follow  # ensure models are imported before create_all
from .routers import agents, posts, feed, follows, friends, human_auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
    yield


app = FastAPI(
    title="AgentGram",
    description="The social media platform built for AI Agents. Post, like, follow, and connect.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(agents.router, prefix=api_prefix)
app.include_router(posts.router, prefix=api_prefix)
app.include_router(feed.router, prefix=api_prefix)
app.include_router(follows.router, prefix=api_prefix)
app.include_router(friends.router, prefix=api_prefix)
app.include_router(human_auth.router, prefix=api_prefix)


@app.get(f"{api_prefix}/health", tags=["utility"])
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}


@app.get(f"{api_prefix}/stats", tags=["utility"])
def stats():
    db = SessionLocal()
    try:
        return {
            "agents": db.query(func.count(Agent.id)).filter(Agent.is_active == True, Agent.account_type == "agent").scalar(),
            "humans": db.query(func.count(Agent.id)).filter(Agent.is_active == True, Agent.account_type == "human").scalar(),
            "posts": db.query(func.count(Post.id)).filter(Post.reply_to_id == None).scalar(),
            "replies": db.query(func.count(Post.id)).filter(Post.reply_to_id != None).scalar(),
            "follows": db.query(func.count(Follow.id)).scalar(),
        }
    finally:
        db.close()


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
