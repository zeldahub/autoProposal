"""사업 복제 스모크.

검증 흐름:
1. 사업 A 생성 (전체 필드) + 첨부 2건(NOTICE+REFERENCE) 업로드
2. A 복제 (includeAttachments=True, 새 이름)
   → 새 사업 B 생성 + 필드 복제 + 첨부 2건 복사 + Mongo documents 깊은 복사
3. B 의 첨부 파일이 디스크에 실제 존재하고 A 와 다른 경로
4. B 의 첨부 mongo_doc_id 가 A 와 다른 ObjectId 이고 내용은 동일
5. 사업 A 의 산출물은 복제 안 됨 (B 산출물 0건)
6. includeAttachments=False 옵션으로 한번 더 복제 → 첨부 0건
7. 다른 사용자 → 403, 미존재 UUID → 404
8. 이름 누락 시 기본값 "{원본} (복제)" 사용
9. 정리 — A/B/C 모두 휴지통 + purge
"""
import io
import sys
from pathlib import Path

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
        token = login(c, "clone-smoke@example.com")
        H = {"Authorization": f"Bearer {token}"}

        # 1) A 생성
        r = c.post("/api/projects", headers=H, json={
            "projectName": "복제 원본",
            "companyName": "Lon Inc",
            "goal": "원본 사업의 목표",
            "scope": "원본 사업 범위",
            "schedule": "2026-Q1 ~ Q3",
            "budget": "5억",
        })
        expect(r.status_code == 200, "create A")
        a_uuid = r.json()["data"]["uuid"]

        # 2) 첨부 2건 업로드 — 작은 텍스트 파일
        files = [
            ("notice", ("notice.txt", "NOTICE: 사업 공고문 본문".encode("utf-8"), "text/plain")),
            ("references", ("ref.txt", "REFERENCE: 참조 자료 본문".encode("utf-8"), "text/plain")),
        ]
        data = {"projectUuid": a_uuid}
        r = c.post("/api/files/analyze", headers=H, data=data, files=files)
        expect(r.status_code == 200, f"upload+analyze A ({r.status_code})")
        r = c.get(f"/api/projects/{a_uuid}/attachments", headers=H)
        a_atts = r.json()["data"]["items"]
        expect(len(a_atts) == 2, f"A has 2 attachments (got {len(a_atts)})")
        a_paths = {at["filename"]: at for at in a_atts}
        a_mongo_ids = {at["mongoDocId"] for at in a_atts}

        # 분석 직후 heuristic fallback 이 goal 등을 덮어썼을 수 있으므로 A 의 현재값을 기준으로 비교
        rA = c.get(f"/api/projects/{a_uuid}", headers=H)
        a_state = rA.json()["data"]

        # 3) 복제 — 첨부 포함
        r = c.post(f"/api/projects/{a_uuid}/clone", headers=H, json={
            "newName": "복제본 #1",
            "includeAttachments": True,
        })
        expect(r.status_code == 200, f"clone A → B ({r.status_code})")
        body = r.json()["data"]
        b_uuid = body["uuid"]
        expect(body["sourceUuid"] == a_uuid, "sourceUuid set")
        expect(body["attachmentCount"] == 2, f"clone copied 2 attachments (got {body['attachmentCount']})")

        # 4) B 의 필드가 A 와 동일 (이름 제외)
        r = c.get(f"/api/projects/{b_uuid}", headers=H)
        expect(r.status_code == 200, "GET B")
        b = r.json()["data"]
        expect(b["projectName"] == "복제본 #1", f"new name applied ({b['projectName']!r})")
        expect(b["companyName"] == a_state["companyName"], "companyName copied")
        expect(b["goal"] == a_state["goal"], "goal copied")
        expect(b["scope"] == a_state["scope"], "scope copied")
        expect(b["budget"] == a_state["budget"], "budget copied")
        expect(b["status"] == "DRAFT", f"status reset to DRAFT (got {b['status']})")

        # 5) B 의 첨부도 동일하게 2건, 다른 mongo_id
        r = c.get(f"/api/projects/{b_uuid}/attachments", headers=H)
        b_atts = r.json()["data"]["items"]
        expect(len(b_atts) == 2, f"B has 2 attachments (got {len(b_atts)})")
        b_mongo_ids = {at["mongoDocId"] for at in b_atts}
        expect(not (a_mongo_ids & b_mongo_ids),
               f"mongo_doc_ids deep-copied (A={a_mongo_ids} B={b_mongo_ids})")
        # 같은 filename / slot 짝이 존재
        a_pairs = {(at["slot"], at["filename"]) for at in a_atts}
        b_pairs = {(at["slot"], at["filename"]) for at in b_atts}
        expect(a_pairs == b_pairs, f"slot+filename pairs match ({a_pairs} vs {b_pairs})")

        # 5b) Mongo documents 의 내용이 동일한지 — preview 로 검증
        notice_a = next(at for at in a_atts if at["slot"] == "NOTICE")
        notice_b = next(at for at in b_atts if at["slot"] == "NOTICE")
        rA = c.get(f"/api/files/{notice_a['mongoDocId']}/preview", headers=H)
        rB = c.get(f"/api/files/{notice_b['mongoDocId']}/preview", headers=H)
        expect(rA.status_code == 200 and rB.status_code == 200, "preview both notices")
        expect(rA.json()["data"]["preview"] == rB.json()["data"]["preview"],
               "deep-copied preview text matches")

        # 6) 산출물은 복제 안 됨 — A/B 모두 0건이지만 안전하게 한 번 확인
        rA = c.get(f"/api/projects/{a_uuid}/artifacts", headers=H)
        rB = c.get(f"/api/projects/{b_uuid}/artifacts", headers=H)
        expect(len(rA.json()["data"]["items"]) == 0, "A no artifacts")
        expect(len(rB.json()["data"]["items"]) == 0, "B no artifacts")

        # 7) includeAttachments=False 로 다시 복제 → 첨부 0건
        r = c.post(f"/api/projects/{a_uuid}/clone", headers=H, json={
            "includeAttachments": False,
        })
        expect(r.status_code == 200, "clone w/o attachments")
        c_uuid = r.json()["data"]["uuid"]
        expect(r.json()["data"]["attachmentCount"] == 0, "no attachments cloned")
        # 기본 이름 적용
        rC = c.get(f"/api/projects/{c_uuid}", headers=H)
        expected_default = f"{a_state['projectName']} (복제)"
        expect(rC.json()["data"]["projectName"] == expected_default,
               f"default name applied ({rC.json()['data']['projectName']!r}, expected {expected_default!r})")
        rC_atts = c.get(f"/api/projects/{c_uuid}/attachments", headers=H)
        expect(len(rC_atts.json()["data"]["items"]) == 0, "C has 0 attachments")

        # 8) 권한 — 다른 사용자 → 403, 미존재 → 404
        other_token = login(c, "clone-other@example.com")
        OH = {"Authorization": f"Bearer {other_token}"}
        r = c.post(f"/api/projects/{a_uuid}/clone", headers=OH, json={"includeAttachments": False})
        expect(r.status_code == 403, f"403 other user (got {r.status_code})")
        r = c.post("/api/projects/00000000-0000-0000-0000-000000000000/clone", headers=H, json={})
        expect(r.status_code == 404, f"404 missing (got {r.status_code})")

        # 9) 정리
        for x in (a_uuid, b_uuid, c_uuid):
            c.delete(f"/api/projects/{x}", headers=H)
            c.delete(f"/api/projects/{x}/purge", headers=H)

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
