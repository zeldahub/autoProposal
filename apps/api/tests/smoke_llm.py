"""LLM 통합 스모크 테스트.

사용법:
  # placeholder 경로 (키 없이)
  python apps/api/tests/smoke_llm.py
  # 실 LLM 호출
  set GEMINI_KEY=AIza...
  python apps/api/tests/smoke_llm.py
"""
import os
import sys
from pathlib import Path

import httpx

BASE = "http://localhost:8089"
KEY = os.environ.get("GEMINI_KEY", "").strip()
PROVIDER = "GEMINI"
MODEL = "gemini-2.5-flash"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c: httpx.Client) -> str:
    r = c.post("/api/auth/register", json={
        "email": "smoke-llm@example.com", "password": "secret123", "displayName": "LlmSmoke"
    })
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": "smoke-llm@example.com", "password": "secret123"})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    notice_text = (
        "사업명: 에코드림 시범사업 정보화 구축\n"
        "사업기간: 2026-06-01 ~ 2026-12-31 (7개월)\n"
        "수행 기관: 서울특별시청 정보통신담당관\n"
        "사업 목표: 친환경 IoT 인프라를 통한 에너지 절감 및 시민 참여 활성화\n"
        "사업 범위: 서울 5개 자치구 시범 운영 (강남, 서초, 송파, 마포, 종로)\n"
        "예산: 1,200,000,000원 (부가세 포함)\n"
        "주요 요구사항:\n"
        "- IoT 센서 5,000개 설치 및 데이터 수집 플랫폼 구축\n"
        "- 시민 대시보드 웹·모바일 (React, Spring Boot)\n"
        "- 보안: SSL/TLS, 개인정보 비식별화, 행안부 PIA 준수\n"
        "- 운영 인력: 시스템 운영 2명, 헬프데스크 1명 (24x7 SLA)\n"
        "- 라이선스: Atlassian JIRA, Confluence (자사 보유분 활용)\n"
    )

    with httpx.Client(base_url=BASE, timeout=120) as c:
        token = login(c)
        H = {"Authorization": f"Bearer {token}"}

        # /files/analyze with optional LLM
        files_form = {"notice": ("notice.txt", notice_text.encode("utf-8"), "text/plain")}
        data = {}
        if KEY:
            data = {"provider": PROVIDER, "model": MODEL, "apiKey": KEY}
            print(f"=== 실 LLM 호출 모드 (Gemini, 키 길이={len(KEY)}) ===")
        else:
            print("=== placeholder 모드 (GEMINI_KEY 미설정) ===")

        r = c.post("/api/files/analyze", headers=H, data=data, files=files_form)
        expect(r.status_code == 200, f"files.analyze {r.status_code}")
        d = r.json()["data"]
        uuid = d["projectUuid"]
        print(f"     projectUuid={uuid}")
        print(f"     llm={d['llm']}")
        if d.get("summary"):
            print(f"     summary={d['summary'][:80]}...")
        print(f"     fields.projectName={d['fields'].get('projectName')!r}")
        print(f"     fields.budget={d['fields'].get('budget')!r}")
        if KEY:
            expect(d["llm"]["used"] is True, "LLM used")
            expect(bool(d["fields"].get("projectName")), "projectName extracted")
            expect(d["confidence"].get("projectName", 0) > 0, "confidence > 0")

        # PPTX 생성 (LLM 옵션 포함)
        body = {"projectUuid": uuid, "categories": ["OVERVIEW", "TECH_REQ"]}
        if KEY:
            body.update({"provider": PROVIDER, "model": MODEL, "apiKey": KEY})

        r = c.post("/api/generate/pptx", headers=H, json=body, timeout=180)
        expect(r.status_code == 200, f"generate.pptx {r.status_code} body={r.text[:200] if r.status_code != 200 else ''}")
        used = r.headers.get("x-llm-used") == "1"
        print(f"     pptx size={len(r.content)} bytes, llm-used={used}")
        out = Path(__file__).parent / "out_proposal.pptx"
        out.write_bytes(r.content)
        if KEY:
            expect(used, "X-LLM-Used header=1")
            expect(len(r.content) > 30_000, "pptx size > 30KB (LLM enriched)")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
