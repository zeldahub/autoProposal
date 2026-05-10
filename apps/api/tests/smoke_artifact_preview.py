"""산출물 미리보기 (PPTX/XLSX 파싱) 스모크 테스트."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

BASE = "http://localhost:8089"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c, email="preview-art-smoke@example.com"):
    r = c.post("/api/auth/register", json={"email": email, "password": "secret123"})
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": email, "password": "secret123"})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    with httpx.Client(base_url=BASE, timeout=60) as c:
        token = login(c)
        H = {"Authorization": f"Bearer {token}"}

        # 사업 1건 + 산출물 2건 (placeholder PPTX/XLSX)
        r = c.post("/api/projects", headers=H, json={
            "projectName": "산출물 미리보기 검증",
            "companyName": "Lon Inc",
            "goal": "PPTX/XLSX preview 테스트",
        })
        expect(r.status_code == 200, "project.create")
        uuid = r.json()["data"]["uuid"]

        r = c.post("/api/generate/pptx", headers=H, json={
            "projectUuid": uuid, "categories": ["OVERVIEW", "TECH_REQ"],
        })
        expect(r.status_code == 200, "generate.pptx")

        r = c.post("/api/generate/wbs", headers=H, json={"projectUuid": uuid, "phases": 5})
        expect(r.status_code == 200, "generate.wbs")

        # 사업의 산출물 목록
        r = c.get(f"/api/projects/{uuid}/artifacts", headers=H)
        items = r.json()["data"]["items"]
        pptx_id = next(a["id"] for a in items if a["type"] == "PPTX")
        xlsx_id = next(a["id"] for a in items if a["type"] == "XLSX")

        # PPTX 미리보기
        r = c.get(f"/api/artifacts/{pptx_id}/preview", headers=H)
        expect(r.status_code == 200, f"preview pptx {r.status_code}")
        d = r.json()["data"]
        expect(d["format"] == "PPTX", "format=PPTX")
        expect(d["totalSlides"] >= 3, f"slides>=3 (got {d['totalSlides']})")
        first = d["slides"][0]
        # 첫 슬라이드는 표지 — 제목이 비어있지 않아야
        expect(bool(first.get("title")), f"first slide title set ({first.get('title')!r})")
        # 카테고리 슬라이드 중 제목에 카테고리명이 들어 있어야
        cat_titles = [s["title"] for s in d["slides"]]
        joined = " | ".join(cat_titles)
        print(f"     pptx titles: {joined[:200]}")
        expect(any("개요" in t or "기술" in t for t in cat_titles), "category title present")

        # XLSX 미리보기
        r = c.get(f"/api/artifacts/{xlsx_id}/preview", headers=H)
        expect(r.status_code == 200, "preview xlsx")
        d = r.json()["data"]
        expect(d["format"] == "XLSX", "format=XLSX")
        expect(d["totalSheets"] >= 1, f"sheets>=1 (got {d['totalSheets']})")
        sheet = d["sheets"][0]
        expect(sheet["totalRows"] >= 5, f"rows>=5 (got {sheet['totalRows']})")
        expect(len(sheet["rows"]) > 0, "rows present")
        # 첫 행이 헤더 (Phase, Task, ...)
        first_row = sheet["rows"][0]
        print(f"     xlsx sheet '{sheet['name']}' first row={first_row}")

        # 권한 — 다른 사용자 → 403
        r = c.post("/api/auth/register", json={"email": "preview-art-other@example.com", "password": "secret123"})
        if r.status_code == 409:
            r = c.post("/api/auth/login", json={"email": "preview-art-other@example.com", "password": "secret123"})
        other_h = {"Authorization": f"Bearer {r.json()['data']['accessToken']}"}
        r = c.get(f"/api/artifacts/{pptx_id}/preview", headers=other_h)
        expect(r.status_code == 403, f"403 for other user (got {r.status_code})")

        # 미존재 ID → 404
        r = c.get("/api/artifacts/9999999/preview", headers=H)
        expect(r.status_code == 404, "non-existent → 404")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
