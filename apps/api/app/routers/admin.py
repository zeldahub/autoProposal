"""ADMIN-01~05 — 관리자 전용."""
from datetime import UTC, datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_

from app.core.deps import AdminDep, DbDep
from app.core.errors import LonError
from app.models import (
    Artifact, AuditLog, LlmCallLog, Project,
    ProposalCategory, User,
)
from app.services import jobs as jobs_svc

router = APIRouter()


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


# ── ADMIN 대시보드 ───────────────────────────────────────
@router.get("/stats")
async def stats(db: DbDep, _admin: AdminDep):
    return _ok({
        "users": db.query(func.count(User.id)).filter(User.deleted_at.is_(None)).scalar() or 0,
        "projects": db.query(func.count(Project.id)).filter(Project.deleted_at.is_(None)).scalar() or 0,
        "artifacts": db.query(func.count(Artifact.id)).scalar() or 0,
        "llmCalls": db.query(func.count(LlmCallLog.id)).scalar() or 0,
        "categories": db.query(func.count(ProposalCategory.id)).scalar() or 0,
        "auditEntries": db.query(func.count(AuditLog.id)).scalar() or 0,
    })


# ── 사용자 ────────────────────────────────────────────────
class UserPatch(BaseModel):
    role: str | None = Field(default=None, pattern="^(USER|ADMIN)$")


@router.get("/users")
async def list_users(
    db: DbDep, _admin: AdminDep,
    q: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=200),
):
    base = db.query(User).filter(User.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        base = base.filter(or_(User.email.like(like), User.display_name.like(like)))
    total = base.count()
    rows = base.order_by(User.created_at.desc()).offset(page * size).limit(size).all()
    return _ok({
        "items": [
            {"id": u.id, "uuid": u.uuid, "email": u.email, "displayName": u.display_name,
             "role": u.role,
             "lastLoginAt": u.last_login_at.isoformat() if u.last_login_at else None,
             "createdAt": u.created_at.isoformat() if u.created_at else None}
            for u in rows
        ],
        "page": page, "size": size, "total": total,
    })


@router.put("/users/{user_id}")
async def update_user(user_id: int, body: UserPatch, db: DbDep, admin: AdminDep):
    if body.role is None:
        raise LonError("LON-ADMIN-400", "변경할 항목이 없습니다.", status=400)
    if user_id == admin.id and body.role != "ADMIN":
        raise LonError("LON-ADMIN-409", "본인의 ADMIN 권한은 회수할 수 없습니다.", status=409)
    u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not u:
        raise LonError("LON-ADMIN-404", "사용자 없음", status=404)
    u.role = body.role
    db.add(AuditLog(user_id=admin.id, action="USER.ROLE_CHANGE",
                    target_type="user", target_uuid=u.uuid,
                    meta_json={"id": u.id, "role": body.role}))
    db.commit()
    return _ok({"id": user_id, "role": body.role})


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: DbDep, admin: AdminDep):
    if user_id == admin.id:
        raise LonError("LON-ADMIN-409", "본인 계정은 삭제할 수 없습니다.", status=409)
    u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not u:
        raise LonError("LON-ADMIN-404", "사용자 없음", status=404)
    u.deleted_at = datetime.now(UTC)
    db.add(AuditLog(user_id=admin.id, action="USER.DELETE",
                    target_type="user", target_uuid=u.uuid))
    db.commit()
    return _ok({"id": user_id, "deleted": True})


# ── 감사 로그 ─────────────────────────────────────────────
@router.get("/audit")
async def list_audit(
    db: DbDep, _admin: AdminDep,
    action: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=50, ge=1, le=200),
):
    base = db.query(AuditLog)
    if action:
        base = base.filter(AuditLog.action.like(f"%{action}%"))
    total = base.count()
    rows = base.order_by(AuditLog.created_at.desc()).offset(page * size).limit(size).all()
    return _ok({
        "items": [
            {"id": r.id, "userId": r.user_id, "action": r.action,
             "targetType": r.target_type, "targetUuid": r.target_uuid,
             "ip": r.ip, "userAgent": r.user_agent, "meta": r.meta_json,
             "createdAt": r.created_at.isoformat() if r.created_at else None}
            for r in rows
        ],
        "page": page, "size": size, "total": total,
    })


@router.get("/jobs")
async def list_jobs(_admin: AdminDep):
    return _ok({"items": jobs_svc.list_jobs_view()})


@router.post("/jobs/{job_id}/run")
async def run_job(job_id: str, _admin: AdminDep):
    try:
        result = await jobs_svc.run_job_now(job_id)
    except KeyError:
        raise LonError("LON-JOB-404", "잡을 찾을 수 없습니다.", status=404)
    return _ok({"id": job_id, "lastRun": result})


@router.put("/jobs/{job_id}/pause")
async def pause_job(job_id: str, _admin: AdminDep):
    if not jobs_svc.pause(job_id):
        raise LonError("LON-JOB-404", "잡을 찾을 수 없습니다.", status=404)
    return _ok({"id": job_id, "paused": True})


@router.put("/jobs/{job_id}/resume")
async def resume_job(job_id: str, _admin: AdminDep):
    if not jobs_svc.resume(job_id):
        raise LonError("LON-JOB-404", "잡을 찾을 수 없습니다.", status=404)
    return _ok({"id": job_id, "paused": False})


# ── 표준 목차 마스터 ──────────────────────────────────────
class CategoryIn(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern="^[A-Z][A-Z0-9_]+$")
    nameKo: str = Field(min_length=1, max_length=80)
    nameEn: str | None = None
    parentId: int | None = None
    sortOrder: int = 50
    slideTemplateKey: str | None = None
    systemPrompt: str | None = None
    systemPromptEn: str | None = None
    isActive: bool = True


class CategoryPatch(BaseModel):
    nameKo: str | None = None
    nameEn: str | None = None
    sortOrder: int | None = None
    slideTemplateKey: str | None = None
    systemPrompt: str | None = None
    systemPromptEn: str | None = None
    isActive: bool | None = None


def _cat_dict(c: ProposalCategory) -> dict:
    return {
        "id": c.id, "code": c.code,
        "nameKo": c.name_ko, "nameEn": c.name_en,
        "parentId": c.parent_id, "sortOrder": c.sort_order,
        "slideTemplateKey": c.slide_template_key,
        "systemPrompt": c.system_prompt,
        "systemPromptEn": c.system_prompt_en,
        "isActive": bool(c.is_active),
        "createdAt": c.created_at.isoformat() if c.created_at else None,
        "updatedAt": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/category")
async def list_categories_admin(db: DbDep, _admin: AdminDep, includeInactive: bool = True):
    q = db.query(ProposalCategory)
    if not includeInactive:
        q = q.filter(ProposalCategory.is_active == 1)
    rows = q.order_by(ProposalCategory.sort_order).all()
    return _ok({"items": [_cat_dict(c) for c in rows]})


@router.post("/category")
async def create_category(body: CategoryIn, db: DbDep, admin: AdminDep):
    dup = db.query(ProposalCategory).filter(ProposalCategory.code == body.code).first()
    if dup:
        raise LonError("LON-CAT-409", "이미 존재하는 코드입니다.", status=409)
    c = ProposalCategory(
        code=body.code, name_ko=body.nameKo, name_en=body.nameEn,
        parent_id=body.parentId, sort_order=body.sortOrder,
        slide_template_key=body.slideTemplateKey,
        system_prompt=body.systemPrompt,
        system_prompt_en=body.systemPromptEn,
        is_active=1 if body.isActive else 0,
    )
    db.add(c)
    db.flush()
    db.add(AuditLog(user_id=admin.id, action="CATEGORY.CREATE",
                    target_type="proposal_category", meta_json={"id": c.id, "code": c.code}))
    db.commit()
    db.refresh(c)
    return _ok(_cat_dict(c))


@router.put("/category/{code}")
async def update_category(code: str, body: CategoryPatch, db: DbDep, admin: AdminDep):
    c = db.query(ProposalCategory).filter(ProposalCategory.code == code).first()
    if not c:
        raise LonError("LON-CAT-404", "카테고리 없음", status=404)
    if body.nameKo is not None:
        c.name_ko = body.nameKo
    if body.nameEn is not None:
        c.name_en = body.nameEn or None
    if body.sortOrder is not None:
        c.sort_order = body.sortOrder
    if body.slideTemplateKey is not None:
        c.slide_template_key = body.slideTemplateKey or None
    if body.systemPrompt is not None:
        c.system_prompt = body.systemPrompt or None
    if body.systemPromptEn is not None:
        c.system_prompt_en = body.systemPromptEn or None
    if body.isActive is not None:
        c.is_active = 1 if body.isActive else 0
    db.add(AuditLog(user_id=admin.id, action="CATEGORY.UPDATE",
                    target_type="proposal_category", meta_json={"id": c.id, "code": c.code}))
    db.commit()
    db.refresh(c)
    return _ok(_cat_dict(c))


@router.delete("/category/{code}")
async def delete_category(code: str, db: DbDep, admin: AdminDep):
    c = db.query(ProposalCategory).filter(ProposalCategory.code == code).first()
    if not c:
        raise LonError("LON-CAT-404", "카테고리 없음", status=404)
    db.delete(c)
    db.add(AuditLog(user_id=admin.id, action="CATEGORY.DELETE",
                    target_type="proposal_category", meta_json={"code": code}))
    db.commit()
    return _ok({"code": code, "deleted": True})
