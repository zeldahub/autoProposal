"""GEN-01/02 — PPTX/XLSX 생성 (LLM-driven 또는 placeholder)."""
import asyncio
import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import DbDep, MongoDep, UserDep
from app.core.errors import LonError
from app.models import Artifact, LlmCallLog, Project, ProposalCategory
from app.services.key_resolver import merge_with_request
from app.services.llm import get_client
from app.services.notify import notify
from app.services.proposal_generator import generate_all
from app.services.pptx_builder import build_proposal_pptx
from app.services.xlsx_builder import build_wbs_xlsx

router = APIRouter()


class GenerateRequest(BaseModel):
    projectUuid: str
    categories: list[str] | None = None
    phases: int = 5
    # LLM 옵션 (없으면 placeholder)
    provider: str | None = None
    model: str | None = None
    apiKey: str | None = None


def _project_to_dict(p: Project) -> dict:
    return {
        "companyName": p.company_name, "projectName": p.project_name,
        "goal": p.goal, "scope": p.scope, "schedule": p.schedule,
        "organization": p.organization, "staff": p.staff,
        "costDev": p.cost_dev, "costOps": p.cost_ops,
        "licenseInfo": p.license_info, "availability": p.availability,
        "budget": p.budget,
    }


def _next_version(db, project_id: int, type_: str) -> int:
    rows = db.execute(
        select(Artifact.version).where(Artifact.project_id == project_id, Artifact.type == type_)
    ).all()
    return (max((r[0] for r in rows), default=0)) + 1


def _resolve_project(db, user, uuid_str: str) -> Project:
    p = db.query(Project).filter(Project.uuid == uuid_str, Project.deleted_at.is_(None)).first()
    if not p:
        raise LonError("LON-PROJ-404", "사업을 찾을 수 없습니다.", status=404)
    if p.owner_id != user.id and user.role != "ADMIN":
        raise LonError("LON-PROJ-403", "권한이 없습니다.", status=403)
    return p


def _resolve_category_pairs(db, codes: list[str] | None) -> list[tuple[str, str]]:
    q = db.query(ProposalCategory).filter(ProposalCategory.is_active == 1)
    if codes:
        q = q.filter(ProposalCategory.code.in_(codes))
    rows = q.order_by(ProposalCategory.sort_order).all()
    return [(r.code, r.name_ko) for r in rows]


@router.post("/pptx")
async def generate_pptx(req: GenerateRequest, db: DbDep, mongo: MongoDep, user: UserDep):
    project = _resolve_project(db, user, req.projectUuid)
    cats = _resolve_category_pairs(db, req.categories)
    if not cats:
        raise LonError("LON-GEN-400", "카테고리가 없습니다.", status=400)

    project_data = _project_to_dict(project)

    # 최근 분석 요약 활용
    last_analysis = mongo["analysisResults"].find_one(
        {"projectUuid": project.uuid}, sort=[("createdAt", -1)]
    )
    summary = (last_analysis or {}).get("summary", "")

    drafts: list[dict] = []
    llm_status: dict = {"used": False}
    llm_call_log_id = None

    eff_provider, eff_model, eff_key, used_setting_id = merge_with_request(
        db, user, req.provider, req.model, req.apiKey,
    )

    if eff_key and eff_provider and eff_model:
        client = get_client(eff_provider, eff_key, eff_model)
        t0 = time.time()
        try:
            results = await generate_all(client, cats, project_data, summary, concurrency=3)
        except Exception as e:  # noqa: BLE001
            raise LonError("LON-GEN-LLM", f"LLM 호출 실패: {e}", status=502) from e
        latency = int((time.time() - t0) * 1000)

        total_in = sum((r.llm_result.input_tokens if r.llm_result else 0) for r in results)
        total_out = sum((r.llm_result.output_tokens if r.llm_result else 0) for r in results)

        for r in results:
            drafts.append({"code": r.code, "name": r.name, "slides": r.slides})

        session = mongo["llmSessions"].insert_one({
            "projectUuid": project.uuid,
            "purpose": "GEN_PPTX",
            "provider": eff_provider,
            "model": eff_model,
            "request": {"categories": [c for c, _ in cats]},
            "response": {"drafts": drafts},
            "usage": {"input": total_in, "output": total_out},
            "latencyMs": latency,
            "createdAt": datetime.now(UTC),
        })
        log = LlmCallLog(
            project_id=project.id, provider=eff_provider, model=eff_model, purpose="GEN_PPTX",
            input_tokens=total_in, output_tokens=total_out, latency_ms=latency,
            http_status=200, mongo_session_id=str(session.inserted_id),
        )
        db.add(log)
        db.flush()
        llm_call_log_id = log.id
        llm_status = {
            "used": True, "latencyMs": latency, "categories": len(drafts),
            "source": "stored" if used_setting_id else "request",
        }
    else:
        # placeholder
        for code, name in cats:
            drafts.append({"code": code, "name": name, "slides": [{
                "title": name, "bullets": ["(LLM 미사용 — 수동 보완 필요)"], "speakerNote": "",
            }]})

    # Mongo proposalDrafts 저장
    version = _next_version(db, project.id, "PPTX")
    draft_id = str(mongo["proposalDrafts"].insert_one({
        "projectUuid": project.uuid,
        "version": version,
        "model": eff_model,
        "categories": drafts,
        "createdAt": datetime.now(UTC),
    }).inserted_id)

    # 파일 생성
    out_dir = Path(settings.workspace_dir) / "outputs" / project.uuid / "pptx"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"v{version}.pptx"
    path = out_dir / filename
    with path.open("wb") as fh:
        build_proposal_pptx(fh, project_uuid=project.uuid, project=project_data, drafts=drafts)

    raw = path.read_bytes()
    db.add(Artifact(
        project_id=project.id, type="PPTX", version=version,
        filename=filename, storage_path=str(path),
        size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
        llm_call_log_id=llm_call_log_id, mongo_draft_id=draft_id,
    ))
    project.status = "GENERATED"
    notify(
        db, user_id=user.id, type="GENERATE", level="SUCCESS",
        title=f"제안서(PPTX) v{version} 생성 완료",
        message=f"{project.project_name} — {len(drafts)}개 카테고리, "
                f"{'LLM 사용' if llm_status['used'] else 'placeholder'}",
        link=f"/projects/{project.uuid}",
        meta={"projectUuid": project.uuid, "type": "PPTX", "version": version,
              "llmUsed": llm_status["used"]},
    )
    db.commit()

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"proposal-{project.uuid[:8]}-{datetime.now().strftime('%Y%m%d%H%M%S')}.pptx",
        headers={"X-LLM-Used": "1" if llm_status["used"] else "0"},
    )


@router.post("/wbs")
async def generate_wbs(req: GenerateRequest, db: DbDep, mongo: MongoDep, user: UserDep):
    project = _resolve_project(db, user, req.projectUuid)
    version = _next_version(db, project.id, "XLSX")
    out_dir = Path(settings.workspace_dir) / "outputs" / project.uuid / "xlsx"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"v{version}.xlsx"
    path = out_dir / filename
    with path.open("wb") as fh:
        build_wbs_xlsx(fh, project_uuid=project.uuid, phases=req.phases)

    raw = path.read_bytes()
    draft_id = str(mongo["wbsTasks"].insert_one({
        "projectUuid": project.uuid,
        "version": version,
        "phases": req.phases,
        "createdAt": datetime.now(UTC),
    }).inserted_id)

    db.add(Artifact(
        project_id=project.id, type="XLSX", version=version,
        filename=filename, storage_path=str(path),
        size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
        mongo_draft_id=draft_id,
    ))
    project.status = "GENERATED"
    notify(
        db, user_id=user.id, type="GENERATE", level="SUCCESS",
        title=f"WBS(XLSX) v{version} 생성 완료",
        message=f"{project.project_name} — {req.phases}단계",
        link=f"/projects/{project.uuid}",
        meta={"projectUuid": project.uuid, "type": "XLSX", "version": version,
              "phases": req.phases},
    )
    db.commit()

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"wbs-{project.uuid[:8]}-{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx",
    )
