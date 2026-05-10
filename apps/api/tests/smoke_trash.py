"""사업 휴지통 (복구 / 영구삭제) 스모크."""
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
    with httpx.Client(base_url=BASE, timeout=60) as c:
        token = login(c, "trash-smoke@example.com")
        H = {"Authorization": f"Bearer {token}"}

        # 사업 2건 생성: A는 복구용, B는 영구삭제용 (산출물 첨부)
        r = c.post("/api/projects", headers=H, json={
            "projectName": "휴지통-복구용", "companyName": "Lon", "goal": "restore test",
        })
        expect(r.status_code == 200, "create A")
        a_uuid = r.json()["data"]["uuid"]

        r = c.post("/api/projects", headers=H, json={
            "projectName": "휴지통-영구삭제용", "companyName": "Lon", "goal": "purge test",
        })
        expect(r.status_code == 200, "create B")
        b_uuid = r.json()["data"]["uuid"]

        # B에 산출물 생성 (PPTX + WBS)
        r = c.post("/api/generate/pptx", headers=H, json={
            "projectUuid": b_uuid, "categories": ["OVERVIEW"],
        })
        expect(r.status_code == 200, "generate.pptx for B")
        r = c.post("/api/generate/wbs", headers=H, json={"projectUuid": b_uuid, "phases": 3})
        expect(r.status_code == 200, "generate.wbs for B")

        # B 산출물 수 확인
        r = c.get(f"/api/projects/{b_uuid}/artifacts", headers=H)
        b_artifacts = r.json()["data"]["items"]
        expect(len(b_artifacts) == 2, f"B has 2 artifacts (got {len(b_artifacts)})")

        # 휴지통 비어있는지
        r = c.get("/api/projects/trash", headers=H)
        expect(r.status_code == 200, "GET /trash")
        baseline_trash = r.json()["data"]["total"]
        print(f"     baseline trash count = {baseline_trash}")

        # A, B 논리 삭제
        r = c.delete(f"/api/projects/{a_uuid}", headers=H)
        expect(r.status_code == 200, "delete A (soft)")
        r = c.delete(f"/api/projects/{b_uuid}", headers=H)
        expect(r.status_code == 200, "delete B (soft)")

        # 휴지통에 2건 추가
        r = c.get("/api/projects/trash", headers=H)
        items = r.json()["data"]["items"]
        uuids_in_trash = [it["uuid"] for it in items]
        expect(a_uuid in uuids_in_trash, "A in trash")
        expect(b_uuid in uuids_in_trash, "B in trash")
        b_in = next(it for it in items if it["uuid"] == b_uuid)
        expect(b_in["artifactCount"] == 2, f"B trash artifactCount=2 (got {b_in['artifactCount']})")
        expect(b_in.get("deletedAt") is not None, "deletedAt set")

        # 일반 사업 목록에서는 안 보여야
        r = c.get("/api/projects", headers=H)
        live_uuids = [it["uuid"] for it in r.json()["data"]["items"]]
        expect(a_uuid not in live_uuids, "A not in live list")
        expect(b_uuid not in live_uuids, "B not in live list")

        # 일반 GET — 삭제된 건은 404
        r = c.get(f"/api/projects/{a_uuid}", headers=H)
        expect(r.status_code == 404, f"GET deleted → 404 (got {r.status_code})")

        # A 복구
        r = c.post(f"/api/projects/{a_uuid}/restore", headers=H)
        expect(r.status_code == 200, "restore A")
        expect(r.json()["data"]["restored"] is True, "restored=true")

        # 복구 후 일반 GET 가능
        r = c.get(f"/api/projects/{a_uuid}", headers=H)
        expect(r.status_code == 200, "GET A after restore")

        # 휴지통에 더 이상 없음
        r = c.get("/api/projects/trash", headers=H)
        uuids = [it["uuid"] for it in r.json()["data"]["items"]]
        expect(a_uuid not in uuids, "A removed from trash")
        expect(b_uuid in uuids, "B still in trash")

        # 살아있는 사업은 복구 불가 → 404 (휴지통에 없음)
        r = c.post(f"/api/projects/{a_uuid}/restore", headers=H)
        expect(r.status_code == 404, f"restore live → 404 (got {r.status_code})")
        # 살아있는 사업은 purge 불가
        r = c.delete(f"/api/projects/{a_uuid}/purge", headers=H)
        expect(r.status_code == 404, f"purge live → 404 (got {r.status_code})")

        # 다른 사용자 → 권한 검사 (휴지통의 B 에 접근)
        other_token = login(c, "trash-other@example.com")
        OH = {"Authorization": f"Bearer {other_token}"}
        r = c.post(f"/api/projects/{b_uuid}/restore", headers=OH)
        expect(r.status_code == 403, f"restore by other → 403 (got {r.status_code})")
        r = c.delete(f"/api/projects/{b_uuid}/purge", headers=OH)
        expect(r.status_code == 403, f"purge by other → 403 (got {r.status_code})")
        # 다른 사용자 휴지통은 자기 것만
        r = c.get("/api/projects/trash", headers=OH)
        uuids = [it["uuid"] for it in r.json()["data"]["items"]]
        expect(b_uuid not in uuids, "other user's trash isolated")

        # B 영구 삭제
        r = c.delete(f"/api/projects/{b_uuid}/purge", headers=H)
        expect(r.status_code == 200, "purge B")
        body = r.json()["data"]
        expect(body["purged"] is True, "purged=true")
        expect(body["artifactCount"] == 2, f"purge artifactCount=2 (got {body['artifactCount']})")

        # B 더 이상 어디에도 없음 — 휴지통에서도, 일반 목록에서도, GET 도 404
        r = c.get(f"/api/projects/{b_uuid}", headers=H)
        expect(r.status_code == 404, f"B gone (got {r.status_code})")
        r = c.get("/api/projects/trash", headers=H)
        uuids = [it["uuid"] for it in r.json()["data"]["items"]]
        expect(b_uuid not in uuids, "B removed from trash")
        # 산출물 다운로드도 404
        if b_artifacts:
            aid = b_artifacts[0]["id"]
            r = c.get(f"/api/artifacts/{aid}/download", headers=H)
            expect(r.status_code == 404, f"purged artifact gone (got {r.status_code})")

        # purge 두 번 → 404
        r = c.delete(f"/api/projects/{b_uuid}/purge", headers=H)
        expect(r.status_code == 404, "double purge → 404")

        # 정리: A 도 삭제 (테스트 잔재 줄이기)
        c.delete(f"/api/projects/{a_uuid}", headers=H)
        c.delete(f"/api/projects/{a_uuid}/purge", headers=H)

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
