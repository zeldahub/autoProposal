"""인앱 알림 (생성 → 목록 → 읽음 → 삭제) 스모크.

검증 흐름:
1. 사용자 가입/로그인
2. 사업 생성 + PPTX/WBS 생성 → 알림 2건 자동 등록되는지 확인
3. unread-count → 2 이상
4. 1건 읽음 처리 → unread-count 감소
5. 클릭 시 link 가 사업 상세 경로인지 확인
6. 다른 사용자 → 알림 격리 (자기 알림만 보임)
7. read-all → unread-count 0
8. 읽은 알림 일괄 삭제 → 목록에서 사라짐
9. 단건 삭제 / 미존재 ID 404
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
    with httpx.Client(base_url=BASE, timeout=60) as c:
        token = login(c, "notif-smoke@example.com")
        H = {"Authorization": f"Bearer {token}"}

        # 정리: 기존 알림 모두 삭제 (read-all → 읽음 일괄 삭제)
        c.post("/api/notifications/read-all", headers=H)
        c.delete("/api/notifications", headers=H)

        # 베이스라인
        r = c.get("/api/notifications/unread-count", headers=H)
        expect(r.status_code == 200, "GET unread-count")
        baseline_unread = r.json()["data"]["count"]
        print(f"     baseline unread = {baseline_unread}")

        # 사업 생성
        r = c.post("/api/projects", headers=H, json={
            "projectName": "알림 스모크", "companyName": "Lon", "goal": "notif test",
        })
        expect(r.status_code == 200, "create project")
        uuid = r.json()["data"]["uuid"]

        # PPTX 생성 → 알림 1건
        r = c.post("/api/generate/pptx", headers=H, json={
            "projectUuid": uuid, "categories": ["OVERVIEW"],
        })
        expect(r.status_code == 200, "generate.pptx")

        # WBS 생성 → 알림 1건
        r = c.post("/api/generate/wbs", headers=H, json={"projectUuid": uuid, "phases": 3})
        expect(r.status_code == 200, "generate.wbs")

        # unread-count 가 2건 증가
        r = c.get("/api/notifications/unread-count", headers=H)
        unread_after = r.json()["data"]["count"]
        expect(unread_after >= baseline_unread + 2, f"unread +2 (got {unread_after} from {baseline_unread})")

        # 목록에 2건이 위쪽에 있어야
        r = c.get("/api/notifications", headers=H, params={"page": 0, "size": 5})
        items = r.json()["data"]["items"]
        expect(len(items) >= 2, f"items >=2 (got {len(items)})")
        latest = items[0]
        expect(latest["type"] == "GENERATE", f"top type=GENERATE (got {latest['type']})")
        expect(latest["link"] == f"/projects/{uuid}", f"link points to project ({latest['link']})")
        expect(latest["readAt"] is None, "top item unread")
        # XLSX/PPTX 둘 중 어느 게 위에 오든 둘 다 GENERATE 여야
        types_top2 = {it["type"] for it in items[:2]}
        expect(types_top2 == {"GENERATE"}, f"top 2 are GENERATE ({types_top2})")
        meta_types = {(it["meta"] or {}).get("type") for it in items[:2]}
        expect(meta_types == {"PPTX", "XLSX"}, f"meta covers PPTX+XLSX ({meta_types})")

        # 1건 읽음 처리
        nid = latest["id"]
        r = c.post(f"/api/notifications/{nid}/read", headers=H)
        expect(r.status_code == 200, "mark read")
        r = c.get("/api/notifications/unread-count", headers=H)
        expect(r.json()["data"]["count"] == unread_after - 1, "unread decreased by 1")

        # 같은 항목 두 번 읽음 → 200 (멱등)
        r = c.post(f"/api/notifications/{nid}/read", headers=H)
        expect(r.status_code == 200, "double read OK")

        # onlyUnread 필터
        r = c.get("/api/notifications", headers=H, params={"onlyUnread": True, "size": 50})
        unread_items = r.json()["data"]["items"]
        expect(all(it["readAt"] is None for it in unread_items), "onlyUnread filter")

        # 다른 사용자 격리
        other_token = login(c, "notif-other@example.com")
        OH = {"Authorization": f"Bearer {other_token}"}
        r = c.get("/api/notifications", headers=OH, params={"size": 50})
        ids_other = {it["id"] for it in r.json()["data"]["items"]}
        ids_mine = {it["id"] for it in items}
        expect(not (ids_other & ids_mine), "other user's notif isolated")
        # 다른 사용자가 내 알림 읽음 → 404
        r = c.post(f"/api/notifications/{nid}/read", headers=OH)
        expect(r.status_code == 404, f"cross-user mark read → 404 (got {r.status_code})")
        r = c.delete(f"/api/notifications/{nid}", headers=OH)
        expect(r.status_code == 404, f"cross-user delete → 404 (got {r.status_code})")

        # read-all
        r = c.post("/api/notifications/read-all", headers=H)
        expect(r.status_code == 200, "read-all")
        r = c.get("/api/notifications/unread-count", headers=H)
        expect(r.json()["data"]["count"] == 0, "all read")

        # 읽은 알림 일괄 삭제
        r = c.delete("/api/notifications", headers=H)
        expect(r.status_code == 200, "delete all read")
        deleted_n = r.json()["data"]["deleted"]
        expect(deleted_n >= 2, f"deleted >=2 (got {deleted_n})")

        # 미존재 ID
        r = c.delete("/api/notifications/9999999", headers=H)
        expect(r.status_code == 404, "delete non-existent → 404")
        r = c.post("/api/notifications/9999999/read", headers=H)
        expect(r.status_code == 404, "read non-existent → 404")

        # 인증 없이 → 401
        r = c.get("/api/notifications")
        expect(r.status_code == 401, "401 without auth")

        # 정리: 사업 + 산출물 정리
        c.delete(f"/api/projects/{uuid}", headers=H)
        c.delete(f"/api/projects/{uuid}/purge", headers=H)

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
