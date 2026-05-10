"""S-200 — AI Provider 키 관리 (CRUD + 테스트 + 활성화).

서버 저장 모델: ai_provider_setting (AES-256-GCM 암호화)
- 키는 응답에 포함하지 않고 마스킹만 노출
- /test 는 저장된 키를 복호화해서 LLM ping
"""
import time
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DbDep, MongoDep, UserDep
from app.core.errors import LonError
from app.core.security import decrypt_secret, encrypt_secret
from app.models import AiProviderSetting, AuditLog, LlmCallLog, Project
from app.services.llm import get_client

router = APIRouter()


def _ok(payload):
    return {"data": payload, "error": None, "traceId": ""}


def _mask(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "•" * len(api_key)
    return f"{api_key[:4]}{'•' * 8}{api_key[-4:]}"


def _to_dict(s: AiProviderSetting, key_preview: str = "") -> dict:
    return {
        "id": s.id,
        "provider": s.provider,
        "alias": s.alias,
        "keyPreview": key_preview,
        "defaultModel": s.default_model,
        "temperature": float(s.temperature) if s.temperature is not None else None,
        "maxTokens": s.max_tokens,
        "isActive": bool(s.is_active),
        "lastVerifiedAt": s.last_verified_at.isoformat() if s.last_verified_at else None,
        "createdAt": s.created_at.isoformat() if s.created_at else None,
    }


def _decrypt(s: AiProviderSetting) -> str:
    return decrypt_secret(s.api_key_cipher, s.key_iv, s.key_tag)


# ── Schemas ──────────────────────────────────────────────
class SettingIn(BaseModel):
    provider: str = Field(pattern="^(OPENAI|GEMINI|ANTHROPIC)$")
    alias: str | None = Field(default=None, max_length=80)
    apiKey: str = Field(min_length=10, max_length=512)
    defaultModel: str | None = Field(default=None, max_length=80)
    temperature: float | None = Field(default=0.4, ge=0, le=2)
    maxTokens: int | None = Field(default=None, ge=1, le=128_000)
    isActive: bool = True


class SettingPatch(BaseModel):
    alias: str | None = None
    apiKey: str | None = Field(default=None, min_length=10, max_length=512)
    defaultModel: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    maxTokens: int | None = Field(default=None, ge=1, le=128_000)
    isActive: bool | None = None


# ── Endpoints ────────────────────────────────────────────
@router.get("")
async def list_settings(db: DbDep, user: UserDep):
    rows = (
        db.query(AiProviderSetting)
        .filter(AiProviderSetting.user_id == user.id)
        .order_by(AiProviderSetting.provider, AiProviderSetting.id)
        .all()
    )
    items = []
    for s in rows:
        try:
            items.append(_to_dict(s, _mask(_decrypt(s))))
        except Exception:  # noqa: BLE001
            items.append(_to_dict(s, "(복호화 실패)"))
    return _ok({"items": items})


@router.get("/active")
async def active_setting(provider: str | None = None, *, db: DbDep, user: UserDep):
    """활성 키 1건 반환 (Generator가 자동 사용). provider 미지정 시 가장 최근 활성."""
    q = db.query(AiProviderSetting).filter(
        AiProviderSetting.user_id == user.id,
        AiProviderSetting.is_active == 1,
    )
    if provider:
        q = q.filter(AiProviderSetting.provider == provider)
    # MariaDB는 NULLS LAST 미지원 → IS NULL 표현식으로 대체
    s = q.order_by(
        AiProviderSetting.last_verified_at.is_(None).asc(),
        AiProviderSetting.last_verified_at.desc(),
        AiProviderSetting.id.desc(),
    ).first()
    if not s:
        return _ok({"setting": None})
    return _ok({"setting": _to_dict(s, _mask(_decrypt(s)))})


@router.post("")
async def create_setting(req: SettingIn, db: DbDep, user: UserDep):
    # 동일 (provider, alias) 중복 차단 — 명시적 충돌 응답
    dup = (
        db.query(AiProviderSetting)
        .filter(
            AiProviderSetting.user_id == user.id,
            AiProviderSetting.provider == req.provider,
            AiProviderSetting.alias == (req.alias or None),
        )
        .first()
    )
    if dup:
        raise LonError("LON-AISET-409", "같은 별칭이 이미 존재합니다.", status=409)

    cipher, iv, tag = encrypt_secret(req.apiKey)
    s = AiProviderSetting(
        user_id=user.id,
        provider=req.provider,
        alias=req.alias,
        api_key_cipher=cipher,
        key_iv=iv,
        key_tag=tag,
        default_model=req.defaultModel,
        temperature=Decimal(str(req.temperature)) if req.temperature is not None else None,
        max_tokens=req.maxTokens,
        is_active=1 if req.isActive else 0,
    )
    db.add(s)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="AISET.CREATE", target_type="ai_provider_setting", target_uuid=None,
                    meta_json={"id": s.id, "provider": req.provider}))
    db.commit()
    db.refresh(s)
    return _ok(_to_dict(s, _mask(req.apiKey)))


@router.put("/{setting_id}")
async def update_setting(setting_id: int, req: SettingPatch, db: DbDep, user: UserDep):
    s = db.query(AiProviderSetting).filter(
        AiProviderSetting.id == setting_id, AiProviderSetting.user_id == user.id,
    ).first()
    if not s:
        raise LonError("LON-AISET-404", "설정을 찾을 수 없습니다.", status=404)

    if req.alias is not None:
        s.alias = req.alias or None
    if req.apiKey:
        cipher, iv, tag = encrypt_secret(req.apiKey)
        s.api_key_cipher = cipher; s.key_iv = iv; s.key_tag = tag
        s.last_verified_at = None  # 재검증 필요
    if req.defaultModel is not None:
        s.default_model = req.defaultModel or None
    if req.temperature is not None:
        s.temperature = Decimal(str(req.temperature))
    if req.maxTokens is not None:
        s.max_tokens = req.maxTokens
    if req.isActive is not None:
        s.is_active = 1 if req.isActive else 0

    db.add(AuditLog(user_id=user.id, action="AISET.UPDATE", target_type="ai_provider_setting",
                    meta_json={"id": s.id}))
    db.commit()
    db.refresh(s)
    return _ok(_to_dict(s, _mask(_decrypt(s))))


@router.delete("/{setting_id}")
async def delete_setting(setting_id: int, db: DbDep, user: UserDep):
    s = db.query(AiProviderSetting).filter(
        AiProviderSetting.id == setting_id, AiProviderSetting.user_id == user.id,
    ).first()
    if not s:
        raise LonError("LON-AISET-404", "설정을 찾을 수 없습니다.", status=404)
    db.delete(s)
    db.add(AuditLog(user_id=user.id, action="AISET.DELETE", target_type="ai_provider_setting",
                    meta_json={"id": setting_id}))
    db.commit()
    return _ok({"id": setting_id, "deleted": True})


@router.post("/{setting_id}/test")
async def test_setting(setting_id: int, db: DbDep, mongo: MongoDep, user: UserDep):
    s = db.query(AiProviderSetting).filter(
        AiProviderSetting.id == setting_id, AiProviderSetting.user_id == user.id,
    ).first()
    if not s:
        raise LonError("LON-AISET-404", "설정을 찾을 수 없습니다.", status=404)
    api_key = _decrypt(s)
    model = s.default_model or "gemini-2.5-flash"

    # 테스트 로그용 임시 사업
    project = (
        db.query(Project)
        .filter(Project.owner_id == user.id, Project.project_name == "(LLM 테스트)")
        .first()
    )
    if project is None:
        project = Project(owner_id=user.id, project_name="(LLM 테스트)")
        db.add(project)
        db.flush()

    client = get_client(s.provider, api_key, model)
    t0 = time.time()
    try:
        echo = await client.ping()
    except Exception as e:  # noqa: BLE001
        latency = int((time.time() - t0) * 1000)
        db.add(LlmCallLog(
            project_id=project.id, provider=s.provider, model=model, purpose="TEST",
            latency_ms=latency, http_status=401, error_code="LON-LLM-401",
        ))
        db.commit()
        raise LonError("LON-LLM-401", f"키 검증 실패: {e}", status=401) from e

    latency = int((time.time() - t0) * 1000)
    s.last_verified_at = datetime.now(UTC)
    session = mongo["llmSessions"].insert_one({
        "projectUuid": project.uuid, "purpose": "TEST",
        "provider": s.provider, "model": model,
        "request": {"messages": [{"role": "user", "content": "pong"}]},
        "response": {"text": echo},
        "usage": {"input": 1, "output": 1},
        "latencyMs": latency,
        "createdAt": datetime.now(UTC),
    })
    db.add(LlmCallLog(
        project_id=project.id, provider=s.provider, model=model, purpose="TEST",
        input_tokens=1, output_tokens=1, latency_ms=latency, http_status=200,
        mongo_session_id=str(session.inserted_id),
    ))
    db.commit()
    return _ok({"ok": True, "latencyMs": latency, "echo": echo})
