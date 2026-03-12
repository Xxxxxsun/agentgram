from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import bcrypt
from ..database import get_db
from ..models.agent import Agent
from ..schemas.human import HumanRegister, HumanLogin, TokenResponse
from ..schemas.agent import AgentPublic
from ..services.jwt import create_token

router = APIRouter(prefix="/auth", tags=["human auth"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_human(body: HumanRegister, db: Session = Depends(get_db)):
    if db.query(Agent).filter(Agent.handle == body.handle).first():
        raise HTTPException(status_code=409, detail={"code": "HANDLE_TAKEN", "message": f"Handle '{body.handle}' is already taken."})
    if db.query(Agent).filter(Agent.email == body.email).first():
        raise HTTPException(status_code=409, detail={"code": "EMAIL_TAKEN", "message": "This email is already registered."})

    user = Agent(
        handle=body.handle,
        display_name=body.display_name,
        email=body.email,
        password_hash=_hash_password(body.password),
        bio=body.bio,
        avatar_url=body.avatar_url,
        account_type="human",
        # humans don't use API keys - set dummy values to satisfy any NOT NULL constraints
        api_key_hash=None,
        api_key_prefix=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    return TokenResponse(
        access_token=token,
        account=AgentPublic.model_validate(user).model_dump(),
    )


@router.post("/login", response_model=TokenResponse)
def login_human(body: HumanLogin, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(Agent).filter(Agent.email == email, Agent.account_type == "human", Agent.is_active == True).first()
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."})

    token = create_token(user.id)
    return TokenResponse(
        access_token=token,
        account=AgentPublic.model_validate(user).model_dump(),
    )
