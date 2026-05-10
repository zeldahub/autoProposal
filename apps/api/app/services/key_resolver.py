"""저장된 active AI 키 조회 헬퍼."""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.security import decrypt_secret
from app.models import AiProviderSetting, User


@dataclass
class ResolvedKey:
    provider: str
    model: str
    api_key: str
    setting_id: int


def resolve_active(db: Session, user: User, provider: str | None = None, model: str | None = None) -> ResolvedKey | None:
    """user 의 활성 키 1건 (옵셔널 provider 필터). 없으면 None."""
    q = db.query(AiProviderSetting).filter(
        AiProviderSetting.user_id == user.id,
        AiProviderSetting.is_active == 1,
    )
    if provider:
        q = q.filter(AiProviderSetting.provider == provider)
    s = q.order_by(
        AiProviderSetting.last_verified_at.is_(None).asc(),
        AiProviderSetting.last_verified_at.desc(),
        AiProviderSetting.id.desc(),
    ).first()
    if not s:
        return None
    try:
        plain = decrypt_secret(s.api_key_cipher, s.key_iv, s.key_tag)
    except Exception:  # noqa: BLE001
        return None
    return ResolvedKey(
        provider=s.provider,
        model=model or s.default_model or "",
        api_key=plain,
        setting_id=s.id,
    )


def merge_with_request(
    db: Session, user: User,
    req_provider: str | None, req_model: str | None, req_key: str | None,
) -> tuple[str | None, str | None, str | None, int | None]:
    """요청 우선, 없으면 저장된 활성 키 사용.

    Returns: (provider, model, apiKey, setting_id_used)
    """
    if req_key and req_provider and req_model:
        return req_provider, req_model, req_key, None
    resolved = resolve_active(db, user, provider=req_provider, model=req_model)
    if resolved and resolved.model:
        return resolved.provider, resolved.model, resolved.api_key, resolved.setting_id
    return req_provider, req_model, req_key, None
