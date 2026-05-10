"""USER-PROFILE — 본인 정보 / 비밀번호 변경."""
import bcrypt
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.deps import DbDep, UserDep
from app.core.errors import LonError
from app.models import AuditLog

router = APIRouter()


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


class ProfilePatch(BaseModel):
    displayName: str | None = Field(default=None, max_length=100)
    locale: str | None = Field(default=None, pattern="^(ko|en)$")


class PasswordChange(BaseModel):
    currentPassword: str = Field(min_length=1)
    newPassword: str = Field(min_length=6, max_length=128)


@router.get("/me")
async def get_me(user: UserDep):
    return _ok({
        "user": {
            "uuid": user.uuid,
            "email": user.email,
            "displayName": user.display_name,
            "locale": user.locale or "ko",
            "role": user.role,
            "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None,
            "createdAt": user.created_at.isoformat() if user.created_at else None,
        }
    })


@router.put("/me")
async def update_me(req: ProfilePatch, db: DbDep, user: UserDep):
    changed = False
    if req.displayName is not None:
        new_name = req.displayName.strip() or None
        if new_name != user.display_name:
            user.display_name = new_name
            changed = True
    if req.locale is not None and req.locale != user.locale:
        user.locale = req.locale
        changed = True
    if changed:
        db.add(AuditLog(user_id=user.id, action="USER.PROFILE_UPDATE",
                        target_type="user", target_uuid=user.uuid))
        db.commit()
        db.refresh(user)
    return _ok({
        "user": {
            "uuid": user.uuid, "email": user.email,
            "displayName": user.display_name,
            "locale": user.locale or "ko",
            "role": user.role,
        }
    })


@router.put("/me/password")
async def change_password(req: PasswordChange, db: DbDep, user: UserDep):
    cur_bytes = req.currentPassword.encode("utf-8")[:72]
    if not bcrypt.checkpw(cur_bytes, user.password_hash.encode("utf-8")):
        raise LonError("LON-USER-401", "현재 비밀번호가 올바르지 않습니다.", status=401)
    new_bytes = req.newPassword.encode("utf-8")[:72]
    if bcrypt.checkpw(new_bytes, user.password_hash.encode("utf-8")):
        raise LonError("LON-USER-400", "새 비밀번호는 현재 비밀번호와 달라야 합니다.", status=400)
    user.password_hash = bcrypt.hashpw(new_bytes, bcrypt.gensalt()).decode("utf-8")
    db.add(AuditLog(user_id=user.id, action="USER.PASSWORD_CHANGE",
                    target_type="user", target_uuid=user.uuid))
    db.commit()
    return _ok({"ok": True})
