"""FILE-01/02 — 첨부 분석 (FS + Maria + Mongo + 선택적 LLM 호출)."""
import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, File, Form, UploadFile

from app.core.config import settings
from app.core.deps import DbDep, MongoDep, UserDep
from app.core.errors import LonError
from app.models import LlmCallLog, Project, ProjectAttachment
from app.services.analysis import analyze as run_analysis
from app.services.file_parser import chunk_text, extract_text
from app.services.key_resolver import merge_with_request
from app.services.llm import get_client

router = APIRouter()

ALLOWED_EXT = {".pdf", ".docx", ".txt", ".md"}
MAX_SIZE = 10 * 1024 * 1024


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


@router.post("/analyze")
async def analyze(
    db: DbDep,
    mongo: MongoDep,
    user: UserDep,
    notice: UploadFile | None = File(default=None),
    references: list[UploadFile] = File(default_factory=list),
    projectUuid: str | None = Form(default=None),
    provider: str | None = Form(default=None),
    model: str | None = Form(default=None),
    apiKey: str | None = Form(default=None),
):
    if notice is None and not references:
        raise LonError("LON-FILE-400", "첨부 파일이 1개 이상 필요합니다.", status=400)

    # Project 확보 (없으면 임시 생성)
    project = None
    if projectUuid:
        project = db.query(Project).filter(Project.uuid == projectUuid).first()
    if project is None:
        project = Project(owner_id=user.id, project_name="(임시) 분석 세션")
        db.add(project)
        db.flush()
        project.project_name = f"(임시) {project.uuid[:8]}"
        db.flush()

    base = Path(settings.workspace_dir) / "attachments" / project.uuid
    base.mkdir(parents=True, exist_ok=True)

    docs_out = []
    notice_text = ""
    reference_texts: list[str] = []

    for f, slot in [(notice, "NOTICE"), *((r, "REFERENCE") for r in references if r)]:
        if f is None:
            continue
        ext = Path(f.filename or "").suffix.lower()
        if ext not in ALLOWED_EXT:
            raise LonError("LON-FILE-EXT", f"허용되지 않는 형식: {ext}", status=400)
        raw = await f.read()
        if len(raw) > MAX_SIZE:
            raise LonError("LON-FILE-413", f"파일 크기 초과: {f.filename}", status=413)

        sha = hashlib.sha256(raw).hexdigest()
        dup = db.query(ProjectAttachment).filter(
            ProjectAttachment.project_id == project.id,
            ProjectAttachment.sha256 == sha,
        ).first()
        if dup:
            docs_out.append({"id": dup.mongo_doc_id, "slot": dup.slot, "filename": dup.filename, "duplicated": True})
            # 중복이라도 LLM 입력에는 포함 (재분석 가능)
            existing_doc = mongo["documents"].find_one({"_id": ObjectId(dup.mongo_doc_id)}) if dup.mongo_doc_id else None
            if existing_doc:
                if dup.slot == "NOTICE":
                    notice_text = existing_doc.get("extractedText", "") or notice_text
                else:
                    reference_texts.append(existing_doc.get("extractedText", ""))
            continue

        safe_name = f.filename.replace("/", "_").replace("\\", "_")
        path = base / f"{uuid4().hex[:8]}_{safe_name}"
        path.write_bytes(raw)

        text = extract_text(safe_name, raw)
        chunks = chunk_text(text)

        ins = mongo["documents"].insert_one({
            "projectUuid": project.uuid,
            "slot": slot,
            "filename": safe_name,
            "mimeType": f.content_type or "application/octet-stream",
            "extractedText": text[:500_000],
            "chunks": chunks,
            "summary": text[:300] + ("..." if len(text) > 300 else ""),
            "language": "ko",
            "createdAt": datetime.now(UTC),
        })
        mongo_id = str(ins.inserted_id)

        att = ProjectAttachment(
            project_id=project.id,
            slot=slot,
            filename=safe_name,
            mime_type=f.content_type or "application/octet-stream",
            size_bytes=len(raw),
            sha256=sha,
            storage_path=str(path),
            mongo_doc_id=mongo_id,
        )
        db.add(att)
        db.flush()

        docs_out.append({"id": mongo_id, "slot": slot, "filename": safe_name, "size": len(raw)})

        if slot == "NOTICE":
            notice_text = text
        else:
            reference_texts.append(text)

    db.commit()

    # ── LLM 분석 (요청 키 또는 저장된 활성 키) ──
    fields: dict[str, str] = {}
    confidence: dict[str, float] = {}
    summary = ""
    llm_status: dict = {"used": False}

    eff_provider, eff_model, eff_key, used_setting_id = merge_with_request(
        db, user, provider, model, apiKey,
    )

    if eff_key and eff_provider and eff_model:
        client = get_client(eff_provider, eff_key, eff_model)
        t0 = time.time()
        try:
            result = await run_analysis(client, notice_text, reference_texts)
            latency = int((time.time() - t0) * 1000)
            session = mongo["llmSessions"].insert_one({
                "projectUuid": project.uuid,
                "purpose": "ANALYZE",
                "provider": eff_provider,
                "model": eff_model,
                "request": {"notice_chars": len(notice_text), "ref_chars": [len(t) for t in reference_texts]},
                "response": {"text": result.llm_result.text if result.llm_result else "", "fields": result.fields},
                "usage": {
                    "input": result.llm_result.input_tokens if result.llm_result else 0,
                    "output": result.llm_result.output_tokens if result.llm_result else 0,
                },
                "latencyMs": latency,
                "createdAt": datetime.now(UTC),
            })
            mongo["analysisResults"].insert_one({
                "projectUuid": project.uuid,
                "fields": result.fields,
                "confidence": result.confidence,
                "summary": result.summary,
                "model": eff_model,
                "createdAt": datetime.now(UTC),
            })
            db.add(LlmCallLog(
                project_id=project.id, provider=eff_provider, model=eff_model, purpose="ANALYZE",
                input_tokens=result.llm_result.input_tokens if result.llm_result else 0,
                output_tokens=result.llm_result.output_tokens if result.llm_result else 0,
                latency_ms=latency, http_status=200,
                mongo_session_id=str(session.inserted_id),
            ))
            db.commit()

            fields = result.fields
            confidence = result.confidence
            summary = result.summary
            llm_status = {
                "used": True, "latencyMs": latency,
                "provider": eff_provider, "model": eff_model,
                "source": "stored" if used_setting_id else "request",
            }
        except Exception as e:  # noqa: BLE001
            latency = int((time.time() - t0) * 1000)
            db.add(LlmCallLog(
                project_id=project.id, provider=eff_provider, model=eff_model, purpose="ANALYZE",
                input_tokens=0, output_tokens=0, latency_ms=latency,
                http_status=500, error_code="LON-LLM-ANALYZE-FAIL",
            ))
            db.commit()
            llm_status = {"used": False, "error": f"LLM 호출 실패: {e}"}

    # LLM 미사용 시 휴리스틱 fallback
    if not fields and notice_text:
        head = notice_text.strip().split("\n", 1)[0][:120]
        fields = {
            "projectName": head or project.project_name,
            "goal": notice_text[:300] + ("..." if len(notice_text) > 300 else ""),
        }
        confidence = {"projectName": 0.3, "goal": 0.2}

    # 자동 필드는 사업 메타에도 반영 (덮어쓰기 — DRAFT 단계만)
    if fields and project.status == "DRAFT":
        if fields.get("projectName"):
            project.project_name = fields["projectName"][:200]
        for f_key, db_attr in [
            ("companyName", "company_name"), ("goal", "goal"), ("scope", "scope"),
            ("schedule", "schedule"), ("organization", "organization"), ("staff", "staff"),
            ("costDev", "cost_dev"), ("costOps", "cost_ops"),
            ("licenseInfo", "license_info"), ("availability", "availability"),
            ("budget", "budget"),
        ]:
            v = fields.get(f_key)
            if v:
                setattr(project, db_attr, v)
        db.commit()

    return _ok({
        "projectUuid": project.uuid,
        "documents": docs_out,
        "fields": fields,
        "confidence": confidence,
        "summary": summary,
        "llm": llm_status,
    })


@router.get("/{file_id}/preview")
async def preview_file(file_id: str, db: DbDep, mongo: MongoDep, user: UserDep):
    """추출된 텍스트 미리보기 — file_id 는 Mongo documents._id."""
    att = db.query(ProjectAttachment).filter(ProjectAttachment.mongo_doc_id == file_id).first()
    if not att:
        raise LonError("LON-FILE-404", "첨부를 찾을 수 없습니다.", status=404)
    # 소유권 검증
    project = db.query(Project).filter(Project.id == att.project_id).first()
    if not project or (project.owner_id != user.id and user.role != "ADMIN"):
        raise LonError("LON-FILE-403", "권한이 없습니다.", status=403)

    doc = mongo["documents"].find_one({"_id": ObjectId(file_id)})
    if not doc:
        raise LonError("LON-FILE-410", "원본 텍스트가 없습니다.", status=410)
    text = doc.get("extractedText") or ""
    return _ok({
        "id": file_id,
        "filename": att.filename,
        "slot": att.slot,
        "mimeType": att.mime_type,
        "sizeBytes": att.size_bytes,
        "language": doc.get("language", "ko"),
        "summary": doc.get("summary") or "",
        "preview": text[:8000],
        "totalChars": len(text),
        "chunkCount": len(doc.get("chunks") or []),
    })


@router.delete("/{file_id}")
async def delete_file(file_id: str, db: DbDep, mongo: MongoDep, user: UserDep):
    att = db.query(ProjectAttachment).filter(ProjectAttachment.mongo_doc_id == file_id).first()
    if not att:
        raise LonError("LON-FILE-404", "첨부를 찾을 수 없습니다.", status=404)
    try:
        Path(att.storage_path).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
    mongo["documents"].delete_one({"_id": ObjectId(file_id)})
    db.delete(att)
    db.commit()
    return _ok({"id": file_id, "deleted": True})
