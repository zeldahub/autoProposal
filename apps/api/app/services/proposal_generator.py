"""사업 정보 → 카테고리별 슬라이드 본문 (LLM)."""
import asyncio
import json
import re
from dataclasses import dataclass, field

from app.services.llm.base import LLMClient, LLMResult

CATEGORY_PROMPTS: dict[str, str] = {
    "OVERVIEW": "사업 배경, 추진 필요성, 기대 효과 중심으로 3~5개 슬라이드.",
    "GENERAL": "사업명/주체/기간/예산/장소 등 일반 사항을 표 형태로 1~2개 슬라이드.",
    "TECH_REQ": "기능/비기능 요구사항을 분류하여 4~6개 슬라이드.",
    "PM_REQ": "사업관리(일정/품질/이슈/위험) 요구사항을 3~4개 슬라이드.",
    "SECURITY": "보안 요구사항(인증/권한/암호화/감사/취약점) 2~3개 슬라이드.",
    "CONSTRAINT": "제약 조건(법령/표준/연계 시스템/환경)을 1~2개 슬라이드.",
    "ETC": "기타 안내·산출물·계약 조건 등 1~2개 슬라이드.",
}

SYSTEM_PROMPT_TEMPLATE = """당신은 한국 공공/민간 SI 사업제안서 작성 전문가입니다.
주어진 사업 정보를 바탕으로 '{category_name}' 카테고리의 PPT 슬라이드 초안을 작성하세요.

규칙:
- 결과는 반드시 JSON 객체 1개만 출력 (앞뒤 설명, markdown 금지).
- 슬라이드는 {style}.
- 각 슬라이드: title(짧은 제목), bullets(3~6개 핵심 포인트), speakerNote(발표용 보조 설명 1~2줄).
- 한국어, 정중체, 과장·허위 금지, 모르는 부분은 "(검토 필요)" 표기.

출력 스키마:
{{
  "slides": [
    {{ "title": "...", "bullets": ["...", "..."], "speakerNote": "..." }}
  ]
}}"""


@dataclass
class CategoryDraft:
    code: str
    name: str
    slides: list[dict] = field(default_factory=list)
    llm_result: LLMResult | None = None
    error: str | None = None


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text.strip())
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _project_block(p: dict) -> str:
    keys = [
        ("회사명", "companyName"), ("사업명", "projectName"),
        ("사업 목표", "goal"), ("사업 범위", "scope"),
        ("일정", "schedule"), ("수행 조직", "organization"),
        ("수행 인력", "staff"), ("개발 비용", "costDev"),
        ("운영 비용", "costOps"), ("라이선스", "licenseInfo"),
        ("가용성", "availability"), ("예산", "budget"),
    ]
    return "\n".join(f"- {ko}: {p.get(en) or '(없음)'}" for ko, en in keys)


async def generate_category(
    client: LLMClient, code: str, name_ko: str, project: dict, summary: str = "",
) -> CategoryDraft:
    style = CATEGORY_PROMPTS.get(code, "3~5개 슬라이드")
    system = SYSTEM_PROMPT_TEMPLATE.format(category_name=name_ko, style=style)
    user = f"### 사업 정보\n{_project_block(project)}\n\n### 공고문 요약\n{summary or '(없음)'}"

    try:
        res = await client.complete(system, user, temperature=0.5, max_tokens=2048)
    except Exception as e:  # noqa: BLE001
        return CategoryDraft(code=code, name=name_ko, error=str(e))

    parsed = _extract_json(res.text)
    slides_raw = parsed.get("slides") or []

    cleaned = []
    for s in slides_raw:
        if not isinstance(s, dict):
            continue
        cleaned.append({
            "title": str(s.get("title", "")).strip()[:200],
            "bullets": [str(b).strip()[:300] for b in (s.get("bullets") or []) if b][:8],
            "speakerNote": str(s.get("speakerNote", "")).strip()[:500],
        })
    if not cleaned:
        cleaned = [{"title": name_ko, "bullets": ["(LLM 응답 파싱 실패 — 수동 보완 필요)"], "speakerNote": ""}]

    return CategoryDraft(code=code, name=name_ko, slides=cleaned, llm_result=res)


async def generate_all(
    client: LLMClient,
    categories: list[tuple[str, str]],
    project: dict,
    summary: str = "",
    concurrency: int = 3,
) -> list[CategoryDraft]:
    sem = asyncio.Semaphore(concurrency)

    async def _one(code, name):
        async with sem:
            return await generate_category(client, code, name, project, summary)

    return await asyncio.gather(*(_one(c, n) for c, n in categories))
