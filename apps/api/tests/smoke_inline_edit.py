"""산출물 인라인 편집 (Step 15) 스모크.

검증 흐름:
1. 사업 생성 + PPTX/XLSX 생성 (placeholder)
2. PPTX preview 로 슬라이드 1 의 title/bullets 확인
3. PPTX 편집 호출 → v2 생성, version 증가
4. v2 preview 에서 변경사항 반영 확인
5. XLSX preview 셀 확인
6. XLSX 편집 호출 → v2 생성
7. v2 preview 에서 변경 확인
8. 정리
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

BASE = "http://localhost:8089"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c, email, pw="secret123"):
    r = c.post("/api/auth/register", json={"email": email, "password": pw})
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": email, "password": pw})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    with httpx.Client(base_url=BASE, timeout=120) as c:
        token = login(c, "edit-smoke@example.com")
        H = {"Authorization": f"Bearer {token}"}

        # 1) 사업 생성
        r = c.post("/api/projects", headers=H, json={"projectName": "편집 스모크 사업"})
        expect(r.status_code == 200, "create project")
        uuid = r.json()["data"]["uuid"]

        # PPTX 생성 (placeholder — apiKey 미지정)
        r = c.post("/api/generate/pptx", headers=H, json={"projectUuid": uuid})
        expect(r.status_code == 200, f"generate PPTX ({r.status_code})")

        # WBS XLSX
        r = c.post("/api/generate/wbs", headers=H, json={"projectUuid": uuid, "phases": 3})
        expect(r.status_code == 200, f"generate XLSX ({r.status_code})")

        # 산출물 목록
        r = c.get(f"/api/projects/{uuid}/artifacts", headers=H)
        items = r.json()["data"]["items"]
        pptx_id = next(a["id"] for a in items if a["type"] == "PPTX")
        xlsx_id = next(a["id"] for a in items if a["type"] == "XLSX")

        # 2) PPTX preview
        r = c.get(f"/api/artifacts/{pptx_id}/preview", headers=H)
        expect(r.status_code == 200, "PPTX preview ok")
        prev = r.json()["data"]
        expect(prev["format"] == "PPTX" and len(prev["slides"]) > 0, "PPTX has slides")

        # 3) PPTX 편집 — 슬라이드 1 title/bullets/note 변경
        r = c.post(f"/api/artifacts/{pptx_id}/edit", headers=H, json={
            "pptxEdits": [{
                "index": 1,
                "title": "편집 테스트 제목",
                "bullets": ["첫 번째 bullet", "두 번째 bullet"],
                "speakerNote": "발표자 노트입니다",
            }],
            "note": "smoke test edit",
        })
        expect(r.status_code == 200, f"PPTX edit ({r.status_code}: {r.text[:200]})")
        body = r.json()["data"]
        expect(body["version"] == 2, f"version=2 (got {body['version']})")
        expect(body["fromArtifactId"] == pptx_id, "fromArtifactId set")
        new_pptx_id = body["id"]

        # 4) v2 preview 확인
        r = c.get(f"/api/artifacts/{new_pptx_id}/preview", headers=H)
        new_prev = r.json()["data"]
        s1 = new_prev["slides"][0]
        expect(s1["title"] == "편집 테스트 제목", f"title applied (got {s1['title']!r})")
        expect("첫 번째 bullet" in s1["bullets"], f"bullet1 applied (got {s1['bullets']!r})")
        expect("발표자 노트입니다" in s1["speakerNote"], f"note applied (got {s1['speakerNote']!r})")

        # 5) XLSX preview
        r = c.get(f"/api/artifacts/{xlsx_id}/preview", headers=H)
        prev_x = r.json()["data"]
        expect(prev_x["format"] == "XLSX" and len(prev_x["sheets"]) > 0, "XLSX has sheets")
        sheet0 = prev_x["sheets"][0]
        sheet_name = sheet0["name"]

        # 6) XLSX 편집 — A1 셀 변경
        r = c.post(f"/api/artifacts/{xlsx_id}/edit", headers=H, json={
            "xlsxEdits": [
                {"sheet": sheet_name, "row": 1, "col": 1, "value": "편집된 헤더"},
                {"sheet": sheet_name, "row": 2, "col": 1, "value": "편집된 데이터"},
            ],
        })
        expect(r.status_code == 200, f"XLSX edit ({r.status_code}: {r.text[:200]})")
        body_x = r.json()["data"]
        expect(body_x["version"] == 2, f"XLSX version=2 (got {body_x['version']})")
        new_xlsx_id = body_x["id"]

        # 7) v2 preview
        r = c.get(f"/api/artifacts/{new_xlsx_id}/preview", headers=H)
        new_prev_x = r.json()["data"]
        s = next(sh for sh in new_prev_x["sheets"] if sh["name"] == sheet_name)
        expect(s["rows"][0][0] == "편집된 헤더", f"A1 applied (got {s['rows'][0][0]!r})")
        expect(s["rows"][1][0] == "편집된 데이터", f"A2 applied (got {s['rows'][1][0]!r})")

        # 권한 검증 — 다른 사용자 → 403
        other = login(c, "edit-other@example.com")
        OH = {"Authorization": f"Bearer {other}"}
        r = c.post(f"/api/artifacts/{pptx_id}/edit", headers=OH, json={"pptxEdits": [{"index": 1, "title": "h"}]})
        expect(r.status_code == 403, f"403 other user (got {r.status_code})")

        # 빈 edits → 400
        r = c.post(f"/api/artifacts/{pptx_id}/edit", headers=H, json={"pptxEdits": []})
        expect(r.status_code == 400, f"400 empty edits (got {r.status_code})")

        # 8) 정리
        c.delete(f"/api/projects/{uuid}", headers=H)
        c.delete(f"/api/projects/{uuid}/purge", headers=H)

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
