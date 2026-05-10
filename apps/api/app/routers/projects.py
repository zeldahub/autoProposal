"""PROJ-01~05 — 사업 CRUD (실 DB + audit_log)."""
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_

from app.core.config import settings
from app.core.deps import DbDep, MongoDep, UserDep
from app.core.errors import LonError
from app.models import Artifact, AuditLog, LlmCallLog, Project, ProjectAttachment

router = APIRouter()


class ProjectIn(BaseModel):
    companyName: str | None = None
    projectName: str = Field(min_length=1, max_length=200)
    goal: str | None = None
    scope: str | None = None
    schedule: str | None = None
    organization: str | None = None
    staff: str | None = None
    costDev: str | None = None
    costOps: str | None = None
    licenseInfo: str | None = None
    availability: str | None = None
    budget: str | None = None
    aiProvider: str | None = None
    aiModel: str | None = None


def _to_dict(p: Project) -> dict:
    return {
        "id": p.id, "uuid": p.uuid, "companyName": p.company_name, "projectName": p.project_name,
        "goal": p.goal, "scope": p.scope, "schedule": p.schedule, "organization": p.organization,
        "staff": p.staff, "costDev": p.cost_dev, "costOps": p.cost_ops, "licenseInfo": p.license_info,
        "availability": p.availability, "budget": p.budget,
        "aiProvider": p.ai_provider, "aiModel": p.ai_model, "status": p.status,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
    }


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


@router.get("/trash")
async def list_trash(
    db: DbDep,
    user: UserDep,
    q: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=200),
):
    """휴지통 — 본인이 논리 삭제한 사업."""
    query = db.query(Project).filter(
        Project.owner_id == user.id, Project.deleted_at.is_not(None)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Project.project_name.like(like), Project.company_name.like(like)))
    total = query.count()
    rows = query.order_by(Project.deleted_at.desc()).offset(page * size).limit(size).all()
    items = []
    for p in rows:
        artifact_count = db.query(Artifact).filter(Artifact.project_id == p.id).count()
        items.append({
            **_to_dict(p),
            "deletedAt": p.deleted_at.isoformat() if p.deleted_at else None,
            "artifactCount": artifact_count,
        })
    return _ok({"items": items, "page": page, "size": size, "total": total})


@router.get("")
async def list_projects(
    db: DbDep,
    user: UserDep,
    q: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=200),
):
    query = db.query(Project).filter(Project.owner_id == user.id, Project.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Project.project_name.like(like), Project.company_name.like(like)))
    total = query.count()
    rows = query.order_by(Project.updated_at.desc()).offset(page * size).limit(size).all()
    return _ok({"items": [_to_dict(r) for r in rows], "page": page, "size": size, "total": total})


@router.post("")
async def create_project(p: ProjectIn, db: DbDep, user: UserDep):
    obj = Project(
        owner_id=user.id,
        company_name=p.companyName, project_name=p.projectName,
        goal=p.goal, scope=p.scope, schedule=p.schedule,
        organization=p.organization, staff=p.staff,
        cost_dev=p.costDev, cost_ops=p.costOps,
        license_info=p.licenseInfo, availability=p.availability,
        budget=p.budget, ai_provider=p.aiProvider, ai_model=p.aiModel,
    )
    db.add(obj)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="PROJECT.CREATE", target_type="project", target_uuid=obj.uuid))
    db.commit()
    db.refresh(obj)
    return _ok({"id": obj.id, "uuid": obj.uuid})


@router.get("/{uuid}")
async def get_project(uuid: str, db: DbDep, user: UserDep):
    p = db.query(Project).filter(Project.uuid == uuid, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    return _ok(_to_dict(p))


@router.put("/{uuid}")
async def update_project(uuid: str, body: ProjectIn, db: DbDep, user: UserDep):
    p = db.query(Project).filter(Project.uuid == uuid, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    p.company_name = body.companyName
    p.project_name = body.projectName
    p.goal = body.goal
    p.scope = body.scope
    p.schedule = body.schedule
    p.organization = body.organization
    p.staff = body.staff
    p.cost_dev = body.costDev
    p.cost_ops = body.costOps
    p.license_info = body.licenseInfo
    p.availability = body.availability
    p.budget = body.budget
    p.ai_provider = body.aiProvider
    p.ai_model = body.aiModel
    db.add(AuditLog(user_id=user.id, action="PROJECT.UPDATE", target_type="project", target_uuid=p.uuid))
    db.commit()
    db.refresh(p)
    return _ok(_to_dict(p))


class CloneRequest(BaseModel):
    newName: str | None = Field(default=None, max_length=200)
    includeAttachments: bool = True


@router.post("/{uuid}/clone")
async def clone_project(uuid: str, req: CloneRequest, db: DbDep, mongo: MongoDep, user: UserDep):
    """기존 사업을 복제 — 필드 + (옵션) 첨부 파일/Mongo 문서까지 복사.

    산출물(artifact), LLM 호출 로그, 분석 결과는 복제하지 않음 (재생성 의도).
    상태(status)는 DRAFT 로 초기화.
    """
    src = db.query(Project).filter(
        Project.uuid == uuid, Project.deleted_at.is_(None)
    ).first()
    if not src:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if src.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)

    base_name = (req.newName or "").strip() or f"{src.project_name} (복제)"
    new_proj = Project(
        owner_id=user.id,
        company_name=src.company_name,
        project_name=base_name[:200],
        goal=src.goal, scope=src.scope, schedule=src.schedule,
        organization=src.organization, staff=src.staff,
        cost_dev=src.cost_dev, cost_ops=src.cost_ops,
        license_info=src.license_info, availability=src.availability,
        budget=src.budget,
        ai_provider=src.ai_provider, ai_model=src.ai_model,
        # status 는 모델 기본값 DRAFT
    )
    db.add(new_proj)
    db.flush()  # new_proj.id / uuid 확보

    cloned_atts = 0
    if req.includeAttachments:
        atts = db.query(ProjectAttachment).filter(
            ProjectAttachment.project_id == src.id
        ).all()
        if atts:
            base_dir = Path(settings.workspace_dir) / "attachments" / new_proj.uuid
            base_dir.mkdir(parents=True, exist_ok=True)

        for a in atts:
            # 1) 파일 복사 (원본 없으면 skip 하지 않고 메타만 복사 — UI 로 재업로드 가능)
            new_file_path: Path | None = None
            try:
                src_path = Path(a.storage_path)
                if src_path.exists():
                    new_file_path = base_dir / f"{uuid4().hex[:8]}_{a.filename}"
                    shutil.copy2(src_path, new_file_path)
            except Exception:  # noqa: BLE001
                new_file_path = None

            # 2) Mongo documents 깊은 복사 (있으면)
            new_mongo_id: str | None = None
            if a.mongo_doc_id:
                try:
                    src_doc = mongo["documents"].find_one({"_id": ObjectId(a.mongo_doc_id)})
                    if src_doc:
                        new_doc = {k: v for k, v in src_doc.items() if k != "_id"}
                        new_doc["projectUuid"] = new_proj.uuid
                        new_doc["createdAt"] = datetime.now(UTC)
                        ins = mongo["documents"].insert_one(new_doc)
                        new_mongo_id = str(ins.inserted_id)
                except Exception:  # noqa: BLE001
                    new_mongo_id = None

            db.add(ProjectAttachment(
                project_id=new_proj.id,
                slot=a.slot,
                filename=a.filename,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
                sha256=a.sha256,
                storage_path=str(new_file_path) if new_file_path else a.storage_path,
                mongo_doc_id=new_mongo_id,
            ))
            cloned_atts += 1

    db.add(AuditLog(
        user_id=user.id, action="PROJECT.CLONE",
        target_type="project", target_uuid=new_proj.uuid,
        meta_json={
            "sourceUuid": src.uuid,
            "includeAttachments": req.includeAttachments,
            "attachmentCount": cloned_atts,
        },
    ))
    db.commit()
    db.refresh(new_proj)

    return _ok({
        "uuid": new_proj.uuid, "id": new_proj.id,
        "sourceUuid": src.uuid,
        "attachmentCount": cloned_atts,
    })


@router.delete("/{uuid}")
async def delete_project(uuid: str, db: DbDep, user: UserDep):
    p = db.query(Project).filter(Project.uuid == uuid, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    p.deleted_at = datetime.now(UTC)
    db.add(AuditLog(user_id=user.id, action="PROJECT.DELETE", target_type="project", target_uuid=p.uuid))
    db.commit()
    return _ok({"uuid": uuid, "deleted": True})


def _check_access(db, user, uuid: str) -> Project:
    p = db.query(Project).filter(Project.uuid == uuid, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    return p


@router.get("/{uuid}/artifacts")
async def list_project_artifacts(uuid: str, db: DbDep, user: UserDep):
    p = _check_access(db, user, uuid)
    rows = (
        db.query(Artifact)
        .filter(Artifact.project_id == p.id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return _ok({"items": [
        {"id": a.id, "type": a.type, "version": a.version, "filename": a.filename,
         "sizeBytes": a.size_bytes,
         "createdAt": a.created_at.isoformat() if a.created_at else None}
        for a in rows
    ]})


@router.get("/{uuid}/attachments")
async def list_project_attachments(uuid: str, db: DbDep, user: UserDep):
    p = _check_access(db, user, uuid)
    rows = (
        db.query(ProjectAttachment)
        .filter(ProjectAttachment.project_id == p.id)
        .order_by(ProjectAttachment.created_at.desc())
        .all()
    )
    return _ok({"items": [
        {
            "id": a.id, "slot": a.slot, "filename": a.filename,
            "mimeType": a.mime_type, "sizeBytes": a.size_bytes,
            "mongoDocId": a.mongo_doc_id,
            "createdAt": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]})


@router.get("/{uuid}/analysis")
async def get_project_analysis(uuid: str, db: DbDep, mongo: MongoDep, user: UserDep):
    """최근 LLM 분석 결과 (fields/confidence/summary)."""
    p = _check_access(db, user, uuid)
    doc = mongo["analysisResults"].find_one(
        {"projectUuid": p.uuid}, sort=[("createdAt", -1)]
    )
    if not doc:
        return _ok({"analysis": None})
    return _ok({"analysis": {
        "fields": doc.get("fields") or {},
        "confidence": doc.get("confidence") or {},
        "summary": doc.get("summary") or "",
        "model": doc.get("model"),
        "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
    }})


@router.get("/{uuid}/llm-logs")
async def list_project_llm_logs(uuid: str, db: DbDep, user: UserDep):
    p = _check_access(db, user, uuid)
    rows = (
        db.query(LlmCallLog)
        .filter(LlmCallLog.project_id == p.id)
        .order_by(LlmCallLog.created_at.desc())
        .limit(100)
        .all()
    )
    return _ok({"items": [
        {"id": r.id, "provider": r.provider, "model": r.model, "purpose": r.purpose,
         "inputTokens": r.input_tokens, "outputTokens": r.output_tokens,
         "latencyMs": r.latency_ms, "httpStatus": r.http_status, "errorCode": r.error_code,
         "createdAt": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]})


def _find_deleted(db, user, uuid: str) -> Project:
    p = db.query(Project).filter(
        Project.uuid == uuid, Project.deleted_at.is_not(None)
    ).first()
    if not p:
        raise LonError("LON-PROJ-404", "휴지통에 해당 사업이 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    return p


@router.post("/{uuid}/restore")
async def restore_project(uuid: str, db: DbDep, user: UserDep):
    """휴지통의 사업을 복구."""
    p = _find_deleted(db, user, uuid)
    p.deleted_at = None
    db.add(AuditLog(user_id=user.id, action="PROJECT.RESTORE",
                    target_type="project", target_uuid=p.uuid))
    db.commit()
    db.refresh(p)
    return _ok({"uuid": uuid, "restored": True})


@router.delete("/{uuid}/purge")
async def purge_project(uuid: str, db: DbDep, mongo: MongoDep, user: UserDep):
    """휴지통의 사업을 영구 삭제 (산출물 파일 + Mongo 문서 + 메타 모두 제거)."""
    p = _find_deleted(db, user, uuid)
    project_id = p.id
    project_uuid = p.uuid

    # 1) 산출물 파일 삭제 + 행 제거
    artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).all()
    for a in artifacts:
        try:
            Path(a.storage_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        if a.mongo_draft_id:
            try:
                mongo["proposalDrafts"].delete_one({"_id": ObjectId(a.mongo_draft_id)})
                mongo["wbsTasks"].delete_one({"_id": ObjectId(a.mongo_draft_id)})
            except Exception:  # noqa: BLE001
                pass
        db.delete(a)

    # 2) 첨부 파일 삭제 + Mongo documents 제거 + 행 제거
    attachments = db.query(ProjectAttachment).filter(
        ProjectAttachment.project_id == project_id
    ).all()
    for att in attachments:
        try:
            Path(att.storage_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        if att.mongo_doc_id:
            try:
                mongo["documents"].delete_one({"_id": ObjectId(att.mongo_doc_id)})
            except Exception:  # noqa: BLE001
                pass
        db.delete(att)

    # 3) LLM 호출 로그 제거
    db.query(LlmCallLog).filter(LlmCallLog.project_id == project_id).delete(
        synchronize_session=False
    )

    # 4) Mongo: projectUuid 기반 컬렉션 정리
    for col in ("analysisResults", "llmSessions", "proposalDrafts", "wbsTasks"):
        try:
            mongo[col].delete_many({"projectUuid": project_uuid})
        except Exception:  # noqa: BLE001
            pass

    # 5) audit + project 행 삭제
    db.add(AuditLog(user_id=user.id, action="PROJECT.PURGE",
                    target_type="project", target_uuid=project_uuid,
                    meta_json={
                        "artifactCount": len(artifacts),
                        "attachmentCount": len(attachments),
                    }))
    db.delete(p)
    db.commit()

    return _ok({
        "uuid": project_uuid, "purged": True,
        "artifactCount": len(artifacts),
        "attachmentCount": len(attachments),
    })
