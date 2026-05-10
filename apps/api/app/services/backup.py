"""백업 서비스 — 사업/사용자 단위 zip 패키지 생성 (in-memory)."""
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from bson import ObjectId


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:120]


def _project_to_export_dict(p) -> dict:
    return {
        "uuid": p.uuid,
        "projectName": p.project_name,
        "companyName": p.company_name,
        "goal": p.goal,
        "scope": p.scope,
        "schedule": p.schedule,
        "organization": p.organization,
        "staff": p.staff,
        "costDev": p.cost_dev,
        "costOps": p.cost_ops,
        "licenseInfo": p.license_info,
        "availability": p.availability,
        "budget": p.budget,
        "aiProvider": p.ai_provider,
        "aiModel": p.ai_model,
        "status": p.status,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
    }


def _att_dict(att) -> dict:
    return {
        "id": att.id, "slot": att.slot, "filename": att.filename,
        "mimeType": att.mime_type, "sizeBytes": att.size_bytes,
        "sha256": att.sha256, "mongoDocId": att.mongo_doc_id,
        "createdAt": att.created_at.isoformat() if att.created_at else None,
    }


def _art_dict(a) -> dict:
    return {
        "id": a.id, "type": a.type, "version": a.version,
        "filename": a.filename, "sizeBytes": a.size_bytes,
        "sha256": a.sha256, "mongoDraftId": a.mongo_draft_id,
        "createdAt": a.created_at.isoformat() if a.created_at else None,
    }


def _comment_dict(c) -> dict:
    return {
        "id": c.id, "userId": c.user_id, "body": c.body,
        "parentId": c.parent_id,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
    }


def write_project_to_zip(zf: zipfile.ZipFile, prefix: str, db, mongo, project) -> dict:
    """zf 안에 prefix/ 디렉토리로 사업 1건의 모든 데이터를 기록.

    구성:
    - prefix/project.json
    - prefix/attachments.json + prefix/attachments/<file>
    - prefix/artifacts.json + prefix/artifacts/<file>
    - prefix/comments.json
    - prefix/analysis/{latest.json}
    - prefix/llm-sessions.jsonl (Mongo)
    """
    from app.models import Artifact, ProjectAttachment, ProjectComment

    counts = {"attachments": 0, "artifacts": 0, "comments": 0, "analyses": 0, "sessions": 0}

    zf.writestr(f"{prefix}/project.json",
                json.dumps(_project_to_export_dict(project), ensure_ascii=False, indent=2))

    # 첨부
    atts = db.query(ProjectAttachment).filter(ProjectAttachment.project_id == project.id).all()
    zf.writestr(f"{prefix}/attachments.json",
                json.dumps([_att_dict(a) for a in atts], ensure_ascii=False, indent=2))
    for a in atts:
        try:
            p = Path(a.storage_path)
            if p.exists():
                zf.write(p, f"{prefix}/attachments/{_safe_name(a.filename)}")
                counts["attachments"] += 1
        except Exception:  # noqa: BLE001
            pass

    # 산출물
    arts = db.query(Artifact).filter(Artifact.project_id == project.id).all()
    zf.writestr(f"{prefix}/artifacts.json",
                json.dumps([_art_dict(a) for a in arts], ensure_ascii=False, indent=2))
    for a in arts:
        try:
            p = Path(a.storage_path)
            if p.exists():
                zf.write(p, f"{prefix}/artifacts/{_safe_name(a.filename)}")
                counts["artifacts"] += 1
        except Exception:  # noqa: BLE001
            pass

    # 댓글
    comments = db.query(ProjectComment).filter(
        ProjectComment.project_id == project.id, ProjectComment.deleted_at.is_(None),
    ).all()
    zf.writestr(f"{prefix}/comments.json",
                json.dumps([_comment_dict(c) for c in comments], ensure_ascii=False, indent=2))
    counts["comments"] = len(comments)

    # 분석 결과 (최신)
    try:
        last = mongo["analysisResults"].find_one({"projectUuid": project.uuid}, sort=[("createdAt", -1)])
        if last:
            last2 = {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in last.items()}
            if "createdAt" in last2 and hasattr(last2["createdAt"], "isoformat"):
                last2["createdAt"] = last2["createdAt"].isoformat()
            zf.writestr(f"{prefix}/analysis/latest.json",
                        json.dumps(last2, ensure_ascii=False, indent=2, default=str))
            counts["analyses"] = 1
    except Exception:  # noqa: BLE001
        pass

    # LLM 세션 로그 (jsonl)
    try:
        sessions = list(mongo["llmSessions"].find({"projectUuid": project.uuid}).sort("createdAt", -1))
        if sessions:
            buf = []
            for s in sessions:
                doc = {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in s.items()}
                if hasattr(doc.get("createdAt"), "isoformat"):
                    doc["createdAt"] = doc["createdAt"].isoformat()
                buf.append(json.dumps(doc, ensure_ascii=False, default=str))
            zf.writestr(f"{prefix}/llm-sessions.jsonl", "\n".join(buf))
            counts["sessions"] = len(sessions)
    except Exception:  # noqa: BLE001
        pass

    return counts


def build_project_zip(db, mongo, project) -> tuple[bytes, dict]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "exportType": "project",
            "exportedAt": datetime.now(UTC).isoformat(),
            "projectUuid": project.uuid,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        prefix = f"projects/{_safe_name(project.uuid)}"
        counts = write_project_to_zip(zf, prefix, db, mongo, project)
        manifest["counts"] = counts
        # manifest 갱신
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return buf.getvalue(), counts


def build_user_zip(db, mongo, user) -> tuple[bytes, dict]:
    from app.models import Project
    buf = io.BytesIO()
    projects = db.query(Project).filter(
        Project.owner_id == user.id, Project.deleted_at.is_(None),
    ).all()
    summary = {"projectCount": len(projects), "projects": []}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "exportType": "user",
            "exportedAt": datetime.now(UTC).isoformat(),
            "ownerEmail": user.email,
            "ownerUuid": user.uuid,
            "projectCount": len(projects),
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for p in projects:
            prefix = f"projects/{_safe_name(p.uuid)}"
            counts = write_project_to_zip(zf, prefix, db, mongo, p)
            summary["projects"].append({"uuid": p.uuid, "name": p.project_name, "counts": counts})
        zf.writestr("summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
    return buf.getvalue(), summary
