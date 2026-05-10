"""FastAPI 의존성: DB / 현재 사용자."""
from typing import Annotated

from fastapi import Depends, Header
from pymongo.database import Database
from sqlalchemy.orm import Session

from app.core.db_maria import get_session_factory
from app.core.db_mongo import get_mongo_db
from app.core.errors import LonError
from app.core.security import decode_token
from app.models import User


def db_session() -> Session:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def mongo() -> Database:
    return get_mongo_db()


def current_user(
    db: Annotated[Session, Depends(db_session)],
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise LonError("LON-AUTH-401", "인증이 필요합니다.", status=401)
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception as e:  # noqa: BLE001
        raise LonError("LON-AUTH-401", f"유효하지 않은 토큰: {e}", status=401) from e

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()
    if not user:
        raise LonError("LON-AUTH-401", "사용자를 찾을 수 없습니다.", status=401)
    return user


def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != "ADMIN":
        raise LonError("LON-AUTH-403", "관리자 권한이 필요합니다.", status=403)
    return user


DbDep = Annotated[Session, Depends(db_session)]
MongoDep = Annotated[Database, Depends(mongo)]
UserDep = Annotated[User, Depends(current_user)]
AdminDep = Annotated[User, Depends(admin_user)]
