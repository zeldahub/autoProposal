"""LLM-01/02 — 키 검증 (llm_call_log + llmSessions 적재)."""
import time
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.deps import DbDep, MongoDep, UserDep
from app.core.errors import LonError
from app.models import LlmCallLog, Project
from app.services.llm import get_client

router = APIRouter()


class TestRequest(BaseModel):
    provider: str = Field(pattern="^(OPENAI|GEMINI|ANTHROPIC)$")
    model: str
    apiKey: str = Field(min_length=10)
    projectUuid: str | None = None


@router.post("/test")
async def test(req: TestRequest, db: DbDep, mongo: MongoDep, user: UserDep):
    client = get_client(req.provider, req.apiKey, req.model)

    # 프로젝트는 필수 아님 — 없으면 user 전용 임시 사업 생성 (테스트 로그용)
    project = None
    if req.projectUuid:
        project = db.query(Project).filter(Project.uuid == req.projectUuid).first()
    if project is None:
        project = db.query(Project).filter(Project.owner_id == user.id, Project.project_name == "(LLM 테스트)").first()
        if project is None:
            project = Project(owner_id=user.id, project_name="(LLM 테스트)")
            db.add(project)
            db.flush()

    t0 = time.time()
    error_code, http_status, echo = None, 200, ""
    try:
        echo = await client.ping()
    except Exception as e:  # noqa: BLE001
        error_code = "LON-LLM-401"
        http_status = 401
        # 로그 적재 후 에러 던짐
        latency = int((time.time() - t0) * 1000)
        session = mongo["llmSessions"].insert_one({
            "projectUuid": project.uuid,
            "purpose": "TEST",
            "provider": req.provider,
            "model": req.model,
            "request": {"messages": [{"role": "user", "content": "pong"}]},
            "response": {"text": "", "raw": {"error": str(e)}},
            "usage": {"input": 0, "output": 0},
            "latencyMs": latency,
            "createdAt": datetime.now(UTC),
        })
        db.add(LlmCallLog(
            project_id=project.id, provider=req.provider, model=req.model, purpose="TEST",
            input_tokens=0, output_tokens=0, latency_ms=latency,
            http_status=http_status, error_code=error_code,
            mongo_session_id=str(session.inserted_id),
        ))
        db.commit()
        raise LonError(error_code, f"키 검증 실패: {e}", status=401) from e

    latency = int((time.time() - t0) * 1000)
    session = mongo["llmSessions"].insert_one({
        "projectUuid": project.uuid,
        "purpose": "TEST",
        "provider": req.provider,
        "model": req.model,
        "request": {"messages": [{"role": "user", "content": "pong"}]},
        "response": {"text": echo},
        "usage": {"input": 1, "output": 1},
        "latencyMs": latency,
        "createdAt": datetime.now(UTC),
    })
    db.add(LlmCallLog(
        project_id=project.id, provider=req.provider, model=req.model, purpose="TEST",
        input_tokens=1, output_tokens=1, latency_ms=latency,
        http_status=http_status, error_code=None,
        mongo_session_id=str(session.inserted_id),
    ))
    db.commit()
    return {"data": {"ok": True, "latencyMs": latency, "echo": echo}, "error": None, "traceId": ""}


@router.get("/status")
async def status(user: UserDep):
    return {
        "data": {"providers": ["OPENAI", "GEMINI", "ANTHROPIC"], "user": user.email},
        "error": None, "traceId": "",
    }
