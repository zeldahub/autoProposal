"""인앱 알림 헬퍼.

`notify(db, user_id, type, title, ...)` — 단일 사용자에게 알림 1건 추가.
`notify_admins(db, ...)` — 모든 ADMIN 사용자에게 알림 일괄 추가 (시스템 잡 결과 등).

DB 세션은 호출자가 관리 — commit 까지 책임진다 (라우터/잡 컨텍스트에 따라
flush 만 필요한 경우도 있음).
"""
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Notification, User


VALID_TYPES = {"GENERATE", "JOB", "SYSTEM", "PROJECT"}
VALID_LEVELS = {"INFO", "SUCCESS", "WARN", "ERROR"}


def notify(
    db: Session,
    *,
    user_id: int,
    type: str,
    title: str,
    message: str | None = None,
    link: str | None = None,
    level: str = "INFO",
    meta: dict | None = None,
    commit: bool = False,
) -> Notification:
    if type not in VALID_TYPES:
        raise ValueError(f"invalid notification type: {type}")
    if level not in VALID_LEVELS:
        raise ValueError(f"invalid notification level: {level}")
    n = Notification(
        user_id=user_id,
        type=type,
        level=level,
        title=title[:200],
        message=(message or None) and message[:500],
        link=link[:255] if link else None,
        meta_json=meta,
    )
    db.add(n)
    if commit:
        db.commit()
        db.refresh(n)
    else:
        db.flush()
    return n


def notify_admins(
    db: Session,
    *,
    type: str = "SYSTEM",
    title: str,
    message: str | None = None,
    link: str | None = None,
    level: str = "INFO",
    meta: dict | None = None,
    commit: bool = False,
) -> int:
    admins: Iterable[User] = (
        db.query(User).filter(User.role == "ADMIN", User.deleted_at.is_(None)).all()
    )
    count = 0
    for a in admins:
        notify(db, user_id=a.id, type=type, title=title, message=message,
               link=link, level=level, meta=meta, commit=False)
        count += 1
    if commit:
        db.commit()
    return count
