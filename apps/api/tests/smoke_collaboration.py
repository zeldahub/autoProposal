"""사업 협업 (Step 17) 스모크.

검증 흐름:
1. owner 사업 A 생성
2. owner 가 user2 에게 READ 공유 추가
3. user2 가 /shared-projects 에서 A 확인
4. user2 가 A 댓글 작성 (소유자에게 알림)
5. owner 가 user2 의 권한을 EDIT 으로 변경
6. user3 (비공유) → 403 (사업 GET 시도)
7. owner 가 공유 해제
8. user2 가 /shared-projects 에서 더 이상 보이지 않음
9. 정리
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
        owner = login(c, "collab-owner@example.com")
        user2 = login(c, "collab-u2@example.com")
        user3 = login(c, "collab-u3@example.com")
        Ho = {"Authorization": f"Bearer {owner}"}
        H2 = {"Authorization": f"Bearer {user2}"}
        H3 = {"Authorization": f"Bearer {user3}"}

        # 1) 사업 생성
        r = c.post("/api/projects", headers=Ho, json={"projectName": "협업 사업 A", "goal": "공유 테스트"})
        expect(r.status_code == 200, "create A")
        a_uuid = r.json()["data"]["uuid"]

        # 2) READ 공유 추가
        r = c.post(f"/api/projects/{a_uuid}/shares", headers=Ho, json={
            "email": "collab-u2@example.com", "role": "READ",
        })
        expect(r.status_code == 200, f"add share ({r.status_code}: {r.text[:200]})")
        share_id = r.json()["data"]["id"]
        expect(r.json()["data"]["role"] == "READ", "role=READ")

        # 중복 추가 — 갱신 (role=EDIT)
        r = c.post(f"/api/projects/{a_uuid}/shares", headers=Ho, json={
            "email": "collab-u2@example.com", "role": "EDIT",
        })
        expect(r.status_code == 200, "upsert share to EDIT")
        expect(r.json()["data"]["role"] == "EDIT", "role updated to EDIT")

        # 3) user2 의 공유받은 목록
        r = c.get("/api/shared-projects", headers=H2)
        expect(r.status_code == 200, f"shared-projects ({r.status_code}: {r.text[:200]})")
        shared = r.json()["data"]["items"]
        expect(any(x["uuid"] == a_uuid for x in shared), "A in shared-projects")
        a_in = next(x for x in shared if x["uuid"] == a_uuid)
        expect(a_in["role"] == "EDIT", "role shown in list")
        expect(a_in["ownerEmail"] == "collab-owner@example.com", "ownerEmail")

        # 4) user2 댓글 작성
        r = c.post(f"/api/projects/{a_uuid}/comments", headers=H2, json={
            "body": "안녕하세요! 협업 댓글 테스트입니다.",
        })
        expect(r.status_code == 200, f"u2 add comment ({r.status_code}: {r.text[:200]})")
        cid = r.json()["data"]["id"]

        # owner 댓글 목록 조회
        r = c.get(f"/api/projects/{a_uuid}/comments", headers=Ho)
        items = r.json()["data"]["items"]
        expect(any(x["id"] == cid for x in items), "comment listed for owner")

        # owner 가 댓글 알림 받았는지
        r = c.get("/api/notifications", headers=Ho, params={"onlyUnread": True})
        notifs = r.json()["data"]["items"]
        expect(any("새 댓글" in n["title"] for n in notifs), "owner got comment notif")

        # 5) 권한 변경 → READ 로 다운그레이드
        r = c.put(f"/api/projects/{a_uuid}/shares/{share_id}", headers=Ho, json={"role": "READ"})
        expect(r.status_code == 200, f"update share to READ ({r.status_code})")
        expect(r.json()["data"]["role"] == "READ", "role=READ")

        # 6) user3 (비공유) → 403
        r = c.get(f"/api/projects/{a_uuid}/comments", headers=H3)
        expect(r.status_code == 403, f"u3 comments → 403 (got {r.status_code})")

        # owner 자체 사업 GET — 200
        r = c.get(f"/api/projects/{a_uuid}", headers=Ho)
        expect(r.status_code == 200, "owner GET A")

        # 7) 공유 해제
        r = c.delete(f"/api/projects/{a_uuid}/shares/{share_id}", headers=Ho)
        expect(r.status_code == 200, "remove share")

        # 8) user2 의 shared-projects 에서 사라짐
        r = c.get("/api/shared-projects", headers=H2)
        items2 = r.json()["data"]["items"]
        expect(not any(x["uuid"] == a_uuid for x in items2), "A no longer in shared-projects")

        # 비소유자 → 공유 추가 시도 → 403
        r = c.post(f"/api/projects/{a_uuid}/shares", headers=H2, json={
            "email": "collab-u3@example.com", "role": "READ",
        })
        expect(r.status_code == 403, f"non-owner share → 403 (got {r.status_code})")

        # 존재하지 않는 사용자 공유 → 404
        r = c.post(f"/api/projects/{a_uuid}/shares", headers=Ho, json={
            "email": "no-such@example.com", "role": "READ",
        })
        expect(r.status_code == 404, f"unknown email → 404 (got {r.status_code})")

        # 본인에게 공유 → 409
        r = c.post(f"/api/projects/{a_uuid}/shares", headers=Ho, json={
            "email": "collab-owner@example.com", "role": "READ",
        })
        expect(r.status_code == 409, f"self-share → 409 (got {r.status_code})")

        # 9) 정리
        c.delete(f"/api/projects/{a_uuid}", headers=Ho)
        c.delete(f"/api/projects/{a_uuid}/purge", headers=Ho)

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
