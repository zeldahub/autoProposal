"""ADMIN 라우트 + RBAC 스모크 테스트."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

BASE = "http://localhost:8089"
ADMIN_EMAIL = "smoke@example.com"     # SQL로 ADMIN 승격됨
USER_EMAIL = "smoke-llm@example.com"  # USER 권한


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c, email, pwd="secret123"):
    r = c.post("/api/auth/login", json={"email": email, "password": pwd})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        admin_h = {"Authorization": f"Bearer {login(c, ADMIN_EMAIL)}"}
        user_h = {"Authorization": f"Bearer {login(c, USER_EMAIL)}"}

        # /auth/me
        r = c.get("/api/auth/me", headers=admin_h)
        expect(r.status_code == 200 and r.json()["data"]["user"]["role"] == "ADMIN", "auth.me admin")
        r = c.get("/api/auth/me", headers=user_h)
        expect(r.json()["data"]["user"]["role"] == "USER", "auth.me user")

        # USER 가 admin 라우트 접근 → 403
        r = c.get("/api/admin/stats", headers=user_h)
        expect(r.status_code == 403, f"USER → /admin/stats = 403 (got {r.status_code})")

        # ADMIN /stats
        r = c.get("/api/admin/stats", headers=admin_h)
        d = r.json()["data"]
        expect(r.status_code == 200 and d["users"] >= 2 and d["categories"] >= 7,
               f"admin.stats users={d.get('users')} cats={d.get('categories')}")

        # ADMIN 사용자 목록
        r = c.get("/api/admin/users", headers=admin_h)
        items = r.json()["data"]["items"]
        expect(len(items) >= 2, f"admin.users count={len(items)}")
        smoke_llm = next(u for u in items if u["email"] == USER_EMAIL)

        # role 토글 USER → ADMIN → USER
        r = c.put(f"/api/admin/users/{smoke_llm['id']}", headers=admin_h, json={"role": "ADMIN"})
        expect(r.status_code == 200 and r.json()["data"]["role"] == "ADMIN", "promote user")
        r = c.put(f"/api/admin/users/{smoke_llm['id']}", headers=admin_h, json={"role": "USER"})
        expect(r.status_code == 200 and r.json()["data"]["role"] == "USER", "demote user")

        # 본인 ADMIN 회수 시도 → 409
        me_id = next(u["id"] for u in items if u["email"] == ADMIN_EMAIL)
        r = c.put(f"/api/admin/users/{me_id}", headers=admin_h, json={"role": "USER"})
        expect(r.status_code == 409, f"self-demote → 409 (got {r.status_code})")

        # 감사 로그
        r = c.get("/api/admin/audit", headers=admin_h)
        d = r.json()["data"]
        expect(r.status_code == 200 and d["total"] >= 1, f"admin.audit total={d['total']}")

        # 감사 검색
        r = c.get("/api/admin/audit?action=USER", headers=admin_h)
        items_a = r.json()["data"]["items"]
        expect(all("USER" in i["action"] for i in items_a), "audit.search action")

        # 카테고리 CRUD
        r = c.get("/api/admin/category", headers=admin_h)
        cats = r.json()["data"]["items"]
        expect(len(cats) >= 7, f"admin.cat list >=7 (got {len(cats)})")

        # 신규
        r = c.post("/api/admin/category", headers=admin_h, json={
            "code": "PROCUREMENT", "nameKo": "조달 사항", "sortOrder": 70,
            "systemPrompt": "조달 항목을 표 형태로 1~2 슬라이드 작성", "isActive": True,
        })
        expect(r.status_code == 200 and r.json()["data"]["code"] == "PROCUREMENT", "cat.create")

        # 중복 차단
        r = c.post("/api/admin/category", headers=admin_h, json={
            "code": "PROCUREMENT", "nameKo": "중복", "sortOrder": 0,
        })
        expect(r.status_code == 409, f"cat.create dup → 409 (got {r.status_code})")

        # 수정
        r = c.put("/api/admin/category/PROCUREMENT", headers=admin_h, json={
            "nameKo": "조달", "isActive": False,
        })
        expect(r.status_code == 200 and r.json()["data"]["isActive"] is False, "cat.update")

        # 비활성 → /api/categories (USER 노출)에서 제외 확인
        r = c.get("/api/categories", headers=user_h)
        public_cats = r.json()["data"]["items"]
        expect(all(c["code"] != "PROCUREMENT" for c in public_cats), "deactivated cat hidden from public")

        # 삭제
        r = c.delete("/api/admin/category/PROCUREMENT", headers=admin_h)
        expect(r.status_code == 200, "cat.delete")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
