"""산출물 라이브러리 — 사용자 전체 산출물 조회/다운로드/삭제/인라인편집."""
import hashlib
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.core.deps import DbDep, UserDep
from app.core.errors import LonError
from app.models import Artifact, AuditLog, Project
from app.services.artifact_editor import apply_pptx_edits, apply_xlsx_edits
from app.services.artifact_preview import preview_pptx, preview_xlsx

router = APIRouter()

MEDIA = {
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


def _to_dict(a: Artifact, project_uuid: str, project_name: str) -> dict:
    return {
        "id": a.id,
        "projectUuid": project_uuid,
        "projectName": project_name,
        "type": a.type,
        "version": a.version,
        "filename": a.filename,
        "sizeBytes": a.size_bytes,
        "createdAt": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("")
async def list_artifacts(
    db: DbDep,
    user: UserDep,
    type: str | None = Query(default=None, pattern="^(PPTX|XLSX)$"),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=200),
):
    """현재 사용자가 소유한 사업의 산출물 목록 (최신 순)."""
    base = (
        db.query(Artifact, Project.uuid, Project.project_name)
        .join(Project, Project.id == Artifact.project_id)
        .filter(Project.owner_id == user.id, Project.deleted_at.is_(None))
    )
    if type:
        base = base.filter(Artifact.type == type)
    total = base.count()
    rows = base.order_by(desc(Artifact.created_at)).offset(page * size).limit(size).all()
    items = [_to_dict(a, p_uuid, p_name) for a, p_uuid, p_name in rows]
    return _ok({"items": items, "page": page, "size": size, "total": total})


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: int, db: DbDep, user: UserDep):
    row = db.execute(
        select(Artifact, Project)
        .join(Project, Project.id == Artifact.project_id)
        .where(Artifact.id == artifact_id, Project.deleted_at.is_(None))
    ).first()
    if not row:
        raise LonError("LON-ART-404", "산출물을 찾을 수 없습니다.", status=404)
    artifact, project = row
    if project.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-ART-403", "권한이 없습니다.", status=403)

    path = Path(artifact.storage_path)
    if not path.exists():
        raise LonError("LON-ART-410", "파일이 존재하지 않습니다 (삭제됨).", status=410)

    return FileResponse(
        path,
        media_type=MEDIA.get(artifact.type, "application/octet-stream"),
        filename=artifact.filename,
    )


@router.get("/{artifact_id}/preview")
async def preview_artifact(artifact_id: int, db: DbDep, user: UserDep):
    row = db.execute(
        select(Artifact, Project)
        .join(Project, Project.id == Artifact.project_id)
        .where(Artifact.id == artifact_id, Project.deleted_at.is_(None))
    ).first()
    if not row:
        raise LonError("LON-ART-404", "산출물을 찾을 수 없습니다.", status=404)
    artifact, project = row
    if project.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-ART-403", "권한이 없습니다.", status=403)

    path = Path(artifact.storage_path)
    if not path.exists():
        raise LonError("LON-ART-410", "파일이 존재하지 않습니다 (삭제됨).", status=410)

    try:
        if artifact.type == "PPTX":
            data = preview_pptx(path)
        elif artifact.type == "XLSX":
            data = preview_xlsx(path)
        else:
            raise LonError("LON-ART-400", f"지원되지 않는 형식: {artifact.type}", status=400)
    except LonError:
        raise
    except Exception as e:  # noqa: BLE001
        raise LonError("LON-ART-500", f"미리보기 파싱 실패: {e}", status=500) from e

    return _ok({
        "id": artifact_id,
        "filename": artifact.filename,
        "type": artifact.type,
        "version": artifact.version,
        "sizeBytes": artifact.size_bytes,
        "createdAt": artifact.created_at.isoformat() if artifact.created_at else None,
        **data,
    })


class PptxSlideEdit(BaseModel):
    index: int = Field(ge=1)
    title: str | None = None
    bullets: list[str] | None = None
    speakerNote: str | None = None


class XlsxCellEditIn(BaseModel):
    sheet: str
    row: int = Field(ge=1)
    col: int = Field(ge=1)
    value: str = ""


class InlineEditRequest(BaseModel):
    pptxEdits: list[PptxSlideEdit] | None = None
    xlsxEdits: list[XlsxCellEditIn] | None = None
    note: str | None = Field(default=None, max_length=500)


@router.post("/{artifact_id}/edit")
async def edit_artifact(artifact_id: int, body: InlineEditRequest, db: DbDep, user: UserDep):
    """원본 산출물을 기반으로 인라인 편집을 적용한 새 버전을 생성한다.

    - PPTX: pptxEdits[].index 별로 title/bullets/speakerNote 갱신
    - XLSX: xlsxEdits[].sheet/row/col 셀 값 갱신
    - 항상 다음 version 으로 새 파일 생성 (원본 보존)
    """
    row = db.execute(
        select(Artifact, Project)
        .join(Project, Project.id == Artifact.project_id)
        .where(Artifact.id == artifact_id, Project.deleted_at.is_(None))
    ).first()
    if not row:
        raise LonError("LON-ART-404", "산출물을 찾을 수 없습니다.", status=404)
    artifact, project = row
    if project.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-ART-403", "권한이 없습니다.", status=403)

    src = Path(artifact.storage_path)
    if not src.exists():
        raise LonError("LON-ART-410", "원본 파일이 존재하지 않습니다.", status=410)

    # 다음 version
    versions = db.execute(
        select(Artifact.version).where(
            Artifact.project_id == project.id, Artifact.type == artifact.type
        )
    ).all()
    next_ver = max((v[0] for v in versions), default=0) + 1

    new_filename = f"v{next_ver}.{'pptx' if artifact.type == 'PPTX' else 'xlsx'}"
    dst = src.parent / new_filename

    if artifact.type == "PPTX":
        edits = [e.model_dump() for e in (body.pptxEdits or [])]
        if not edits:
            raise LonError("LON-ART-EDIT-400", "pptxEdits 가 비어 있습니다.", status=400)
        applied = apply_pptx_edits(src, dst, edits)
    elif artifact.type == "XLSX":
        edits = [e.model_dump() for e in (body.xlsxEdits or [])]
        if not edits:
            raise LonError("LON-ART-EDIT-400", "xlsxEdits 가 비어 있습니다.", status=400)
        applied = apply_xlsx_edits(src, dst, edits)
    else:
        raise LonError("LON-ART-400", f"지원되지 않는 형식: {artifact.type}", status=400)

    raw = dst.read_bytes()
    new_artifact = Artifact(
        project_id=project.id,
        type=artifact.type,
        version=next_ver,
        filename=new_filename,
        storage_path=str(dst),
        size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        llm_call_log_id=None,
        mongo_draft_id=artifact.mongo_draft_id,
    )
    db.add(new_artifact)
    db.add(AuditLog(
        user_id=user.id, action="ARTIFACT.EDIT",
        target_type="artifact", target_uuid=str(artifact.id),
        meta_json={
            "newArtifactId": None,  # flush 후 채움
            "type": artifact.type,
            "fromVersion": artifact.version,
            "toVersion": next_ver,
            "applied": applied,
            "note": body.note,
        },
    ))
    db.flush()
    db.commit()

    return _ok({
        "id": new_artifact.id,
        "type": new_artifact.type,
        "version": new_artifact.version,
        "filename": new_artifact.filename,
        "sizeBytes": new_artifact.size_bytes,
        "applied": applied,
        "fromArtifactId": artifact.id,
        "fromVersion": artifact.version,
    })


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: int, db: DbDep, user: UserDep):
    row = db.execute(
        select(Artifact, Project)
        .join(Project, Project.id == Artifact.project_id)
        .where(Artifact.id == artifact_id, Project.deleted_at.is_(None))
    ).first()
    if not row:
        raise LonError("LON-ART-404", "산출물을 찾을 수 없습니다.", status=404)
    artifact, project = row
    if project.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-ART-403", "권한이 없습니다.", status=403)

    try:
        Path(artifact.storage_path).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
    db.delete(artifact)
    db.commit()
    return _ok({"id": artifact_id, "deleted": True})
