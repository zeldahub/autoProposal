"""첨부 미리보기 + analysisResults 시드 + 분석 조회 스모크 테스트.

가짜 키로는 실제 LLM 분석이 안 되므로, Mongo 에 직접 analysisResults 한 건을 시드하고
GET /projects/{uuid}/analysis 가 그것을 반환하는지 검증합니다.
"""
import io
import sys
from datetime import UTC, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx
from pymongo import MongoClient

BASE = "http://localhost:8089"
MONGO_URL = "mongodb://lon_app:CHANGE_ME_LON_2026@127.0.0.1:27017/lon?authSource=lon"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c, email="preview-smoke@example.com"):
    r = c.post("/api/auth/register", json={"email": email, "password": "secret123"})
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": email, "password": "secret123"})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    mongo = MongoClient(MONGO_URL).get_default_database()

    with httpx.Client(base_url=BASE, timeout=30) as c:
        token = login(c)
        H = {"Authorization": f"Bearer {token}"}

        # 1) 사업 + 첨부 (LLM 키 없이 → 휴리스틱 fallback)
        notice = "사업명: 미리보기 검증용 사업\n사업 목표: 첨부 미리보기 + confidence 시각화\n사업 범위: 미리보기 drawer 표시\n".encode("utf-8")
        r = c.post("/api/files/analyze", headers=H,
                   files={"notice": ("notice.txt", notice, "text/plain")})
        expect(r.status_code == 200, "files.analyze")
        d = r.json()["data"]
        uuid = d["projectUuid"]
        mongo_doc_id = d["documents"][0]["id"]
        print(f"     uuid={uuid} mongoDocId={mongo_doc_id}")

        # 2) attachments 목록
        r = c.get(f"/api/projects/{uuid}/attachments", headers=H)
        items = r.json()["data"]["items"]
        expect(r.status_code == 200 and len(items) == 1, f"attachments count={len(items)}")
        expect(items[0]["mongoDocId"] == mongo_doc_id, "attachment.mongoDocId matches")

        # 3) /files/{id}/preview
        r = c.get(f"/api/files/{mongo_doc_id}/preview", headers=H)
        expect(r.status_code == 200, f"file preview {r.status_code}")
        p = r.json()["data"]
        expect("미리보기" in p["preview"] or "사업명" in p["preview"], "preview text contains source")
        expect(p["totalChars"] > 0 and p["chunkCount"] >= 1, f"chars={p['totalChars']} chunks={p['chunkCount']}")
        print(f"     summary={p['summary'][:60]}...")

        # 4) analysis 미수행 시 null
        r = c.get(f"/api/projects/{uuid}/analysis", headers=H)
        expect(r.status_code == 200 and r.json()["data"]["analysis"] is None, "analysis=null initially")

        # 5) Mongo에 직접 analysisResults 1건 시드
        mongo["analysisResults"].insert_one({
            "projectUuid": uuid,
            "fields": {
                "projectName": "미리보기 검증용 사업",
                "goal": "첨부 미리보기 + confidence 시각화",
                "scope": "미리보기 drawer 표시",
                "budget": "10,000,000원",
            },
            "confidence": {
                "projectName": 0.95, "goal": 0.85, "scope": 0.62, "budget": 0.30,
            },
            "summary": "스모크 테스트로 시드된 분석 결과입니다.",
            "model": "gemini-2.5-flash",
            "createdAt": datetime.now(UTC),
        })

        # 6) 다시 조회
        r = c.get(f"/api/projects/{uuid}/analysis", headers=H)
        a = r.json()["data"]["analysis"]
        expect(a is not None, "analysis present")
        expect(a["fields"]["projectName"] == "미리보기 검증용 사업", "analysis.fields.projectName")
        expect(0.9 < a["confidence"]["projectName"] < 1.0, f"confidence high (got {a['confidence']['projectName']})")
        expect(a["confidence"]["budget"] < 0.5, "confidence low for budget")

        # 7) 다른 사용자 → 403
        r = c.post("/api/auth/register", json={"email": "preview-other@example.com", "password": "secret123"})
        if r.status_code == 409:
            r = c.post("/api/auth/login", json={"email": "preview-other@example.com", "password": "secret123"})
        other_h = {"Authorization": f"Bearer {r.json()['data']['accessToken']}"}
        r = c.get(f"/api/files/{mongo_doc_id}/preview", headers=other_h)
        expect(r.status_code == 403, f"other user preview = 403 (got {r.status_code})")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
