"""AUTH-01/02/03 — 로그인/등록 (bcrypt + JWT)."""
from datetime import UTC, datetime

import bcrypt
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from app.core.deps import DbDep, UserDep
from app.core.errors import LonError
from app.core.security import create_access_token
from app.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    displayName: str | None = None


def _ok(payload: dict):
    return {"data": payload, "error": None, "traceId": ""}


@router.post("/register")
async def register(req: RegisterRequest, db: DbDep):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise LonError("LON-AUTH-409", "이미 가입된 이메일입니다.", status=409)
    pwd_bytes = req.password.encode("utf-8")[:72]
    user = User(
        email=req.email,
        password_hash=bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8"),
        display_name=req.displayName or req.email.split("@")[0],
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(sub=user.email, ttl_min=60)
    return _ok({"accessToken": token, "tokenType": "Bearer", "user": {"email": user.email, "uuid": user.uuid}})


@router.post("/login")
async def login(req: LoginRequest, db: DbDep):
    user = db.query(User).filter(User.email == req.email, User.deleted_at.is_(None)).first()
    pwd_bytes = req.password.encode("utf-8")[:72]
    if not user or not bcrypt.checkpw(pwd_bytes, user.password_hash.encode("utf-8")):
        raise LonError("LON-AUTH-401", "이메일 또는 비밀번호가 올바르지 않습니다.", status=401)
    user.last_login_at = datetime.now(UTC)
    db.commit()
    token = create_access_token(sub=user.email, ttl_min=60)
    return _ok({"accessToken": token, "tokenType": "Bearer", "user": {"email": user.email, "uuid": user.uuid, "role": user.role}})


@router.post("/logout")
async def logout():
    return _ok({"ok": True})


@router.post("/refresh")
async def refresh():
    return _ok({"accessToken": "TODO"})


@router.get("/me")
async def me(user: UserDep):
    return _ok({
        "user": {
            "uuid": user.uuid, "email": user.email,
            "displayName": user.display_name, "role": user.role,
        }
    })
