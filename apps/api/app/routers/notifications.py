"""NOTIF — 인앱 알림 (목록/읽음/삭제)."""
from datetime import UTC, datetime

from fastapi import APIRouter, Query
from sqlalchemy import func

from app.core.deps import DbDep, UserDep
from app.core.errors import LonError
from app.models import Notification

router = APIRouter()


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "level": n.level,
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "meta": n.meta_json,
        "readAt": n.read_at.isoformat() if n.read_at else None,
        "createdAt": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
async def list_notifications(
    db: DbDep,
    user: UserDep,
    onlyUnread: bool = Query(default=False),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
):
    base = db.query(Notification).filter(Notification.user_id == user.id)
    if onlyUnread:
        base = base.filter(Notification.read_at.is_(None))
    total = base.count()
    rows = (
        base.order_by(Notification.created_at.desc())
        .offset(page * size).limit(size).all()
    )
    return _ok({
        "items": [_to_dict(n) for n in rows],
        "page": page, "size": size, "total": total,
    })


@router.get("/unread-count")
async def unread_count(db: DbDep, user: UserDep):
    cnt = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .scalar() or 0
    )
    return _ok({"count": cnt})


@router.post("/{nid}/read")
async def mark_read(nid: int, db: DbDep, user: UserDep):
    n = db.query(Notification).filter(
        Notification.id == nid, Notification.user_id == user.id
    ).first()
    if not n:
        raise LonError("LON-NOTIF-404", "알림을 찾을 수 없습니다.", status=404)
    if n.read_at is None:
        n.read_at = datetime.now(UTC)
        db.commit()
    return _ok({"id": nid, "read": True})


@router.post("/read-all")
async def mark_all_read(db: DbDep, user: UserDep):
    now = datetime.now(UTC)
    n = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .update({Notification.read_at: now}, synchronize_session=False)
    )
    db.commit()
    return _ok({"updated": n or 0})


@router.delete("/{nid}")
async def delete_notification(nid: int, db: DbDep, user: UserDep):
    n = db.query(Notification).filter(
        Notification.id == nid, Notification.user_id == user.id
    ).first()
    if not n:
        raise LonError("LON-NOTIF-404", "알림을 찾을 수 없습니다.", status=404)
    db.delete(n)
    db.commit()
    return _ok({"id": nid, "deleted": True})


@router.delete("")
async def delete_all_read(db: DbDep, user: UserDep):
    """읽음 상태 알림을 일괄 삭제."""
    n = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read_at.is_not(None))
        .delete(synchronize_session=False)
    )
    db.commit()
    return _ok({"deleted": n or 0})
