"""Listings/Detail/Artifacts 스모크 테스트."""
import sys

import httpx

BASE = "http://localhost:8089"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c: httpx.Client) -> str:
    r = c.post("/api/auth/register", json={
        "email": "list-smoke@example.com", "password": "secret123", "displayName": "ListSmoke"
    })
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": "list-smoke@example.com", "password": "secret123"})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        token = login(c)
        H = {"Authorization": f"Bearer {token}"}

        # 1) 사업 1건 생성
        r = c.post("/api/projects", headers=H, json={
            "projectName": "리스트 검증용 사업", "companyName": "Lon Inc",
            "goal": "목록/상세 페이지 검증", "aiProvider": "GEMINI", "aiModel": "gemini-2.5-flash",
        })
        expect(r.status_code == 200, "project.create")
        uuid = r.json()["data"]["uuid"]

        # 2) PPTX/WBS 생성 (placeholder)
        for kind, body in [
            ("pptx", {"projectUuid": uuid, "categories": ["OVERVIEW"]}),
            ("wbs", {"projectUuid": uuid, "phases": 5}),
        ]:
            r = c.post(f"/api/generate/{kind}", headers=H, json=body)
            expect(r.status_code == 200 and len(r.content) > 1000, f"generate.{kind}")

        # 3) 사업 목록
        r = c.get("/api/projects", headers=H)
        d = r.json()["data"]
        expect(r.status_code == 200 and d["total"] >= 1, f"projects.list total={d['total']}")

        # 4) 검색
        r = c.get("/api/projects?q=리스트", headers=H)
        d = r.json()["data"]
        expect(r.status_code == 200 and d["total"] >= 1, "projects.list?q=…")

        # 5) 사업 상세
        r = c.get(f"/api/projects/{uuid}", headers=H)
        expect(r.status_code == 200 and r.json()["data"]["projectName"] == "리스트 검증용 사업", "projects.detail")

        # 6) 사업별 산출물
        r = c.get(f"/api/projects/{uuid}/artifacts", headers=H)
        items = r.json()["data"]["items"]
        expect(r.status_code == 200 and len(items) == 2, f"projects.artifacts count={len(items)}")
        pptx_id = next(a["id"] for a in items if a["type"] == "PPTX")

        # 7) 사업별 LLM 로그 (placeholder 모드라 0건 정상)
        r = c.get(f"/api/projects/{uuid}/llm-logs", headers=H)
        expect(r.status_code == 200, "projects.llm-logs")

        # 8) 산출물 라이브러리
        r = c.get("/api/artifacts", headers=H)
        d = r.json()["data"]
        expect(r.status_code == 200 and d["total"] >= 2, f"artifacts.list total={d['total']}")

        # 9) 산출물 필터
        r = c.get("/api/artifacts?type=PPTX", headers=H)
        d = r.json()["data"]
        expect(r.status_code == 200 and all(i["type"] == "PPTX" for i in d["items"]), "artifacts.filter=PPTX")

        # 10) 다운로드
        r = c.get(f"/api/artifacts/{pptx_id}/download", headers=H)
        expect(r.status_code == 200 and len(r.content) > 1000, f"artifact.download size={len(r.content)}")

        # 11) 사업 수정
        r = c.put(f"/api/projects/{uuid}", headers=H, json={
            "projectName": "리스트 검증용 사업 v2", "companyName": "Lon Inc", "scope": "범위 갱신",
        })
        expect(r.status_code == 200 and r.json()["data"]["projectName"].endswith("v2"), "project.update")

        # 12) 산출물 삭제
        wbs_id = next(a["id"] for a in items if a["type"] == "XLSX")
        r = c.delete(f"/api/artifacts/{wbs_id}", headers=H)
        expect(r.status_code == 200, "artifact.delete")

        # 13) 권한 (다른 사용자)
        r = c.post("/api/auth/register", json={"email": "other@example.com", "password": "secret123"})
        if r.status_code == 409:
            r = c.post("/api/auth/login", json={"email": "other@example.com", "password": "secret123"})
        other_h = {"Authorization": f"Bearer {r.json()['data']['accessToken']}"}
        r = c.get(f"/api/projects/{uuid}", headers=other_h)
        expect(r.status_code == 403, f"403 for other user (got {r.status_code})")
        r = c.get(f"/api/artifacts/{pptx_id}/download", headers=other_h)
        expect(r.status_code == 403, f"download 403 for other user (got {r.status_code})")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
