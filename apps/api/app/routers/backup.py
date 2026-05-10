"""백업/내보내기 — 사업/사용자 단위 zip 패키지."""
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import Response

from app.core.deps import DbDep, MongoDep, UserDep
from app.core.errors import LonError
from app.models import AuditLog, Project
from app.services.backup import build_project_zip, build_user_zip

router = APIRouter()


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


def _zip_response(content: bytes, name: str) -> Response:
    # RFC 5987: 비ASCII 파일명을 UTF-8 으로 인코딩 (filename* 사용)
    ascii_safe = "".join(ch if ord(ch) < 128 else "_" for ch in name)
    encoded = quote(name)
    cd = f"attachment; filename=\"{ascii_safe}\"; filename*=UTF-8''{encoded}"
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": cd,
            "Content-Length": str(len(content)),
        },
    )


@router.get("/projects/{uuid}/export")
async def export_project(uuid: str, db: DbDep, mongo: MongoDep, user: UserDep):
    """단일 사업의 모든 데이터를 zip 으로 다운로드 (소유자/관리자)."""
    p = db.query(Project).filter(Project.uuid == uuid, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)

    content, counts = build_project_zip(db, mongo, p)
    db.add(AuditLog(
        user_id=user.id, action="PROJECT.EXPORT",
        target_type="project", target_uuid=p.uuid,
        meta_json={"sizeBytes": len(content), **counts},
    ))
    db.commit()

    safe_name = "".join(c if c.isalnum() else "_" for c in (p.project_name or "project"))[:40]
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return _zip_response(content, f"lon-{safe_name}-{ts}.zip")


@router.get("/me/export-all")
async def export_all_my_projects(db: DbDep, mongo: MongoDep, user: UserDep):
    """본인 소유 모든 사업을 한 zip 으로 백업."""
    content, summary = build_user_zip(db, mongo, user)
    db.add(AuditLog(
        user_id=user.id, action="USER.EXPORT_ALL",
        target_type="user", target_uuid=user.uuid,
        meta_json={"sizeBytes": len(content), "projectCount": summary["projectCount"]},
    ))
    db.commit()
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return _zip_response(content, f"lon-backup-{user.email.split('@')[0]}-{ts}.zip")


@router.get("/me/export-summary")
async def export_summary(db: DbDep, user: UserDep):
    """미리 보기 — 백업 시 포함될 사업 수와 추정 크기."""
    rows = db.query(Project).filter(
        Project.owner_id == user.id, Project.deleted_at.is_(None),
    ).all()
    return _ok({
        "projectCount": len(rows),
        "projects": [
            {"uuid": p.uuid, "name": p.project_name, "status": p.status}
            for p in rows
        ],
    })
