"""공고문/관련 산출물 → 12 필드 추출 (LLM)."""
import json
import re
from dataclasses import dataclass, field

from app.services.llm.base import LLMClient, LLMResult

FIELDS = [
    "companyName", "projectName", "goal", "scope", "schedule",
    "organization", "staff", "costDev", "costOps",
    "licenseInfo", "availability", "budget",
]

SYSTEM_PROMPT = """당신은 한국의 공공/민간 SI 사업제안서 작성 전문가입니다.
사용자가 제공한 사업공고문(NOTICE)과 관련 산출물(REFERENCE)에서 아래 12개 필드를 추출/정리하세요.

규칙:
- 결과는 반드시 JSON 객체 1개만 출력 (앞뒤 markdown, 설명 금지).
- 모르는 값은 빈 문자열 "" 또는 null.
- confidence는 각 필드별 0~1 신뢰도 (0=추정 없음, 1=원문에 명시).
- 한국어로 작성, 단위 보존(예: "1,200,000,000원").
- "projectName"은 사업명만 (조사·서론 제거).

출력 스키마:
{
  "fields": {
    "companyName": "", "projectName": "", "goal": "", "scope": "",
    "schedule": "", "organization": "", "staff": "",
    "costDev": "", "costOps": "", "licenseInfo": "", "availability": "", "budget": ""
  },
  "confidence": {
    "companyName": 0.0, "projectName": 0.0, "goal": 0.0, "scope": 0.0,
    "schedule": 0.0, "organization": 0.0, "staff": 0.0,
    "costDev": 0.0, "costOps": 0.0, "licenseInfo": 0.0, "availability": 0.0, "budget": 0.0
  },
  "summary": "공고문 핵심 요약 2~3문장"
}"""


@dataclass
class AnalysisResult:
    fields: dict[str, str] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    summary: str = ""
    llm_result: LLMResult | None = None


def _extract_json(text: str) -> dict:
    """LLM이 markdown fence/설명을 섞어도 첫 JSON 블록 추출."""
    if not text:
        return {}
    # ```json ... ``` 제거
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text.strip())
    # 첫 { ... } 블록
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


async def analyze(client: LLMClient, notice_text: str, reference_texts: list[str]) -> AnalysisResult:
    parts = []
    if notice_text:
        parts.append(f"### NOTICE\n{notice_text[:8000]}")
    for i, t in enumerate(reference_texts):
        parts.append(f"### REFERENCE-{i+1}\n{t[:4000]}")
    user_prompt = "\n\n".join(parts) if parts else "(첨부 없음)"

    res = await client.complete(SYSTEM_PROMPT, user_prompt, temperature=0.3, max_tokens=2048)
    parsed = _extract_json(res.text)

    fields = parsed.get("fields") or {}
    # 누락 필드 보정
    for k in FIELDS:
        fields.setdefault(k, "")
        if fields[k] is None:
            fields[k] = ""

    confidence = parsed.get("confidence") or {}
    for k in FIELDS:
        try:
            confidence[k] = float(confidence.get(k, 0.0))
        except (TypeError, ValueError):
            confidence[k] = 0.0

    return AnalysisResult(
        fields=fields,
        confidence=confidence,
        summary=parsed.get("summary", "") or "",
        llm_result=res,
    )
