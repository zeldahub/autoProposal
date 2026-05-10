"""End-to-end 스모크 테스트.

실행: python apps/api/tests/smoke.py
"""
import sys
from pathlib import Path

import httpx

BASE = "http://localhost:8089"


def expect(cond, label):
    mark = "OK" if cond else "FAIL"
    print(f"  [{mark}] {label}")
    if not cond:
        sys.exit(1)


def main():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        # 0) healthz
        r = c.get("/healthz")
        expect(r.status_code == 200, f"healthz {r.status_code}")

        # 1) register
        email = "smoke@example.com"
        r = c.post("/api/auth/register", json={
            "email": email, "password": "secret123", "displayName": "Smoke"
        })
        if r.status_code == 409:
            r = c.post("/api/auth/login", json={"email": email, "password": "secret123"})
        expect(r.status_code == 200, f"register/login {r.status_code} body={r.text[:200]}")
        token = r.json()["data"]["accessToken"]
        H = {"Authorization": f"Bearer {token}"}

        # 2) categories
        r = c.get("/api/categories")
        expect(r.status_code == 200 and len(r.json()["data"]["items"]) == 7, "categories=7")

        # 3) project create
        r = c.post("/api/projects", headers=H, json={
            "projectName": "에코드림(ecoDream)",
            "companyName": "Lon Inc",
            "goal": "AI 사업제안서 자동화",
            "scope": "공공/민간 SI 표준 목차 자동 생성",
            "budget": "1,200,000,000원",
            "aiProvider": "GEMINI",
            "aiModel": "gemini-2.5-flash",
        })
        expect(r.status_code == 200, f"project.create {r.status_code} body={r.text[:200]}")
        uuid = r.json()["data"]["uuid"]
        print(f"     uuid={uuid}")

        # 4) project list
        r = c.get("/api/projects?page=0&size=10", headers=H)
        expect(r.status_code == 200 and r.json()["data"]["total"] >= 1, "project.list >=1")

        # 5) project detail
        r = c.get(f"/api/projects/{uuid}", headers=H)
        expect(r.status_code == 200 and r.json()["data"]["projectName"] == "에코드림(ecoDream)", "project.detail")

        # 6) project update
        r = c.put(f"/api/projects/{uuid}", headers=H, json={
            "projectName": "에코드림(ecoDream) v2",
            "companyName": "Lon Inc",
            "scope": "범위 v2",
        })
        expect(r.status_code == 200 and r.json()["data"]["projectName"].endswith("v2"), "project.update")

        # 7) files analyze
        notice_text = (
            "사업명: 에코드림 시범사업\n"
            "사업 목표: 친환경 IoT 인프라 구축\n"
            "사업 범위: 서울 5개 자치구 시범 운영\n"
        )
        r = c.post(
            "/api/files/analyze",
            headers=H,
            data={"projectUuid": uuid},
            files={"notice": ("notice.txt", notice_text.encode("utf-8"), "text/plain")},
        )
        expect(r.status_code == 200, f"files.analyze {r.status_code} body={r.text[:200]}")
        d = r.json()["data"]
        expect(len(d["documents"]) == 1, "documents=1")
        print(f"     fields.projectName={d['fields'].get('projectName', '(no notice fields)')}")

        # 8) llm test (가짜 키 → 401 + 로그 적재 검증)
        r = c.post("/api/llm/test", headers=H, json={
            "provider": "GEMINI", "model": "gemini-2.5-flash", "apiKey": "AIzaTESTONLY", "projectUuid": uuid
        })
        body = r.json()
        expect(r.status_code == 401 and body["error"]["code"] == "LON-LLM-401", "llm.test → LON-LLM-401")

        # 9) generate PPTX
        r = c.post("/api/generate/pptx", headers=H, json={
            "projectUuid": uuid, "categories": ["OVERVIEW", "TECH_REQ", "SECURITY"],
        })
        expect(r.status_code == 200 and len(r.content) > 5000, f"generate.pptx size={len(r.content)}")
        Path(__file__).parent.joinpath("proposal.pptx").write_bytes(r.content)  # noqa

        # 10) generate WBS
        r = c.post("/api/generate/wbs", headers=H, json={"projectUuid": uuid, "phases": 5})
        expect(r.status_code == 200 and len(r.content) > 1000, f"generate.wbs size={len(r.content)}")
        Path(__file__).parent.joinpath("wbs.xlsx").write_bytes(r.content)  # noqa

        # 11) project detail again — status가 GENERATED 인지
        r = c.get(f"/api/projects/{uuid}", headers=H)
        expect(r.json()["data"]["status"] == "GENERATED", "project.status=GENERATED")

        # 12) project soft-delete
        r = c.delete(f"/api/projects/{uuid}", headers=H)
        expect(r.status_code == 200, "project.delete")
        r = c.get(f"/api/projects/{uuid}", headers=H)
        expect(r.status_code == 404, "project.detail after delete=404")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
