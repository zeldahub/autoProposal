"""COLLAB — 사업 공유 + 댓글."""
from datetime import UTC, datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_

from app.core.deps import DbDep, UserDep
from app.core.errors import LonError
from app.models import AuditLog, Project, ProjectComment, ProjectShare, User
from app.services.notify import notify

router = APIRouter()


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


def _resolve_project_for_admin(db, user, uuid: str) -> Project:
    """소유자만 권한 부여 가능 (관리자 포함)."""
    p = db.query(Project).filter(Project.uuid == uuid, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    return p


def _resolve_project_for_view(db, user, uuid: str) -> tuple[Project, str]:
    """소유자/공유받은자/관리자가 접근 가능. role 반환: OWNER|EDIT|READ|ADMIN."""
    p = db.query(Project).filter(Project.uuid == uuid, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id == user.id:
        return p, "OWNER"
    if user.role == "ADMIN":
        return p, "ADMIN"
    share = db.query(ProjectShare).filter(
        ProjectShare.project_id == p.id, ProjectShare.user_id == user.id,
    ).first()
    if not share:
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    return p, share.role


# ── Shares ──────────────────────────────────────────────────
class ShareIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(default="READ", pattern="^(READ|EDIT)$")


class SharePatch(BaseModel):
    role: str = Field(pattern="^(READ|EDIT)$")


def _share_dict(s: ProjectShare, u: User | None) -> dict:
    return {
        "id": s.id,
        "userId": s.user_id,
        "userEmail": u.email if u else None,
        "userDisplayName": u.display_name if u else None,
        "role": s.role,
        "grantedBy": s.granted_by,
        "createdAt": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/projects/{uuid}/shares")
async def list_shares(uuid: str, db: DbDep, user: UserDep):
    p = _resolve_project_for_admin(db, user, uuid)
    rows = db.query(ProjectShare, User).join(User, User.id == ProjectShare.user_id).filter(
        ProjectShare.project_id == p.id
    ).order_by(ProjectShare.created_at.desc()).all()
    return _ok({
        "items": [_share_dict(s, u) for (s, u) in rows],
        "owner": {"id": p.owner_id},
    })


@router.post("/projects/{uuid}/shares")
async def add_share(uuid: str, body: ShareIn, db: DbDep, user: UserDep):
    p = _resolve_project_for_admin(db, user, uuid)
    target = db.query(User).filter(User.email == body.email, User.deleted_at.is_(None)).first()
    if not target:
        raise LonError("LON-COLLAB-USER-404", f"사용자를 찾을 수 없습니다: {body.email}", status=404)
    if target.id == p.owner_id:
        raise LonError("LON-COLLAB-409", "소유자에게는 공유할 수 없습니다.", status=409)
    existing = db.query(ProjectShare).filter(
        ProjectShare.project_id == p.id, ProjectShare.user_id == target.id,
    ).first()
    if existing:
        existing.role = body.role
        s = existing
    else:
        s = ProjectShare(project_id=p.id, user_id=target.id, role=body.role, granted_by=user.id)
        db.add(s)
    db.add(AuditLog(
        user_id=user.id, action="PROJECT.SHARE_ADD",
        target_type="project", target_uuid=p.uuid,
        meta_json={"granteeId": target.id, "role": body.role},
    ))
    notify(
        db, user_id=target.id, type="PROJECT", level="INFO",
        title=f"사업이 공유되었습니다: {p.project_name}",
        message=f"{user.email} 님이 '{p.project_name}' 을(를) {body.role} 권한으로 공유했습니다.",
        link=f"/projects/{p.uuid}",
        meta={"projectUuid": p.uuid, "role": body.role},
    )
    db.commit()
    db.refresh(s)
    return _ok(_share_dict(s, target))


@router.put("/projects/{uuid}/shares/{share_id}")
async def update_share(uuid: str, share_id: int, body: SharePatch, db: DbDep, user: UserDep):
    p = _resolve_project_for_admin(db, user, uuid)
    s = db.query(ProjectShare).filter(
        ProjectShare.id == share_id, ProjectShare.project_id == p.id,
    ).first()
    if not s:
        raise LonError("LON-COLLAB-404", "공유 항목을 찾을 수 없습니다.", status=404)
    s.role = body.role
    db.add(AuditLog(
        user_id=user.id, action="PROJECT.SHARE_UPDATE",
        target_type="project", target_uuid=p.uuid,
        meta_json={"shareId": share_id, "role": body.role},
    ))
    db.commit()
    target = db.query(User).filter(User.id == s.user_id).first()
    return _ok(_share_dict(s, target))


@router.delete("/projects/{uuid}/shares/{share_id}")
async def remove_share(uuid: str, share_id: int, db: DbDep, user: UserDep):
    p = _resolve_project_for_admin(db, user, uuid)
    s = db.query(ProjectShare).filter(
        ProjectShare.id == share_id, ProjectShare.project_id == p.id,
    ).first()
    if not s:
        raise LonError("LON-COLLAB-404", "공유 항목을 찾을 수 없습니다.", status=404)
    db.delete(s)
    db.add(AuditLog(
        user_id=user.id, action="PROJECT.SHARE_REMOVE",
        target_type="project", target_uuid=p.uuid,
        meta_json={"shareId": share_id, "userId": s.user_id},
    ))
    db.commit()
    return _ok({"id": share_id, "deleted": True})


# 본인이 공유받은 사업 목록
@router.get("/shared-projects")
async def shared_with_me(
    db: DbDep, user: UserDep,
    page: int = Query(default=0, ge=0), size: int = Query(default=20, ge=1, le=200),
):
    base = (
        db.query(ProjectShare, Project, User)
        .join(Project, Project.id == ProjectShare.project_id)
        .join(User, User.id == Project.owner_id)
        .filter(
            ProjectShare.user_id == user.id,
            Project.deleted_at.is_(None),
        )
    )
    total = base.count()
    rows = base.order_by(ProjectShare.created_at.desc()).offset(page * size).limit(size).all()
    items = [{
        "uuid": p.uuid, "projectName": p.project_name,
        "companyName": p.company_name, "status": p.status,
        "ownerEmail": owner.email,
        "role": s.role,
        "sharedAt": s.created_at.isoformat() if s.created_at else None,
    } for (s, p, owner) in rows]
    return _ok({"items": items, "page": page, "size": size, "total": total})


# ── Comments ────────────────────────────────────────────────
class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    parentId: int | None = None


def _comment_dict(c: ProjectComment, u: User | None) -> dict:
    return {
        "id": c.id, "userId": c.user_id,
        "userEmail": u.email if u else None,
        "userDisplayName": u.display_name if u else None,
        "body": c.body,
        "parentId": c.parent_id,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
        "updatedAt": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/projects/{uuid}/comments")
async def list_comments(uuid: str, db: DbDep, user: UserDep):
    p, _ = _resolve_project_for_view(db, user, uuid)
    rows = db.query(ProjectComment, User).join(User, User.id == ProjectComment.user_id).filter(
        ProjectComment.project_id == p.id, ProjectComment.deleted_at.is_(None),
    ).order_by(ProjectComment.created_at.asc()).all()
    return _ok({"items": [_comment_dict(c, u) for (c, u) in rows]})


@router.post("/projects/{uuid}/comments")
async def add_comment(uuid: str, body: CommentIn, db: DbDep, user: UserDep):
    p, role = _resolve_project_for_view(db, user, uuid)
    # READ 도 댓글 가능 (단순화)
    parent = None
    if body.parentId:
        parent = db.query(ProjectComment).filter(
            ProjectComment.id == body.parentId,
            ProjectComment.project_id == p.id,
            ProjectComment.deleted_at.is_(None),
        ).first()
        if not parent:
            raise LonError("LON-COLLAB-404", "부모 댓글을 찾을 수 없습니다.", status=404)
    c = ProjectComment(
        project_id=p.id, user_id=user.id, body=body.body.strip(),
        parent_id=parent.id if parent else None,
    )
    db.add(c)
    db.add(AuditLog(
        user_id=user.id, action="PROJECT.COMMENT_ADD",
        target_type="project", target_uuid=p.uuid,
        meta_json={"commentLen": len(body.body)},
    ))
    # 소유자에게 알림 (본인 댓글 제외)
    if p.owner_id != user.id:
        notify(
            db, user_id=p.owner_id, type="PROJECT", level="INFO",
            title=f"새 댓글: {p.project_name}",
            message=body.body[:120] + ("..." if len(body.body) > 120 else ""),
            link=f"/projects/{p.uuid}",
            meta={"projectUuid": p.uuid, "from": user.email},
        )
    db.commit()
    db.refresh(c)
    return _ok(_comment_dict(c, user))


@router.delete("/projects/{uuid}/comments/{comment_id}")
async def delete_comment(uuid: str, comment_id: int, db: DbDep, user: UserDep):
    p, _ = _resolve_project_for_view(db, user, uuid)
    c = db.query(ProjectComment).filter(
        ProjectComment.id == comment_id,
        ProjectComment.project_id == p.id,
        ProjectComment.deleted_at.is_(None),
    ).first()
    if not c:
        raise LonError("LON-COLLAB-404", "댓글을 찾을 수 없습니다.", status=404)
    if c.user_id != user.id and user.role != "ADMIN" and user.id != p.owner_id:
        raise LonError("LON-COLLAB-403", "본인 또는 사업 소유자만 삭제할 수 있습니다.", status=403)
    c.deleted_at = datetime.now(UTC)
    db.add(AuditLog(
        user_id=user.id, action="PROJECT.COMMENT_DELETE",
        target_type="project", target_uuid=p.uuid,
        meta_json={"commentId": comment_id},
    ))
    db.commit()
    return _ok({"id": comment_id, "deleted": True})
