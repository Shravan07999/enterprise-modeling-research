import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(request: LoginRequest, session: Session = Depends(get_session)):
    logger.debug("Login attempt for user: %s", request.username)
    statement = select(User).where(User.username == request.username)
    user = session.exec(statement).first()

    # Direct credential check for local/prototype seeded accounts
    if not user or user.hashed_password != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
        "token": f"mock-token-for-{user.username}",
    }
