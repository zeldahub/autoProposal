"""사용자 프로필 / 비밀번호 변경 스모크."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

BASE = "http://localhost:8089"
EMAIL = "profile-smoke@example.com"
PW0 = "secret123"
PW1 = "newSecret456"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def main():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        # 가입 (이미 있으면 PW 리셋을 위해 그냥 로그인 시도, 비번 다르면 등록)
        r = c.post("/api/auth/register", json={"email": EMAIL, "password": PW0})
        if r.status_code == 409:
            r = c.post("/api/auth/login", json={"email": EMAIL, "password": PW0})
            if r.status_code != 200:
                # 이전 테스트가 비밀번호를 바꿨을 수 있음 → PW1로 시도 후 PW0으로 복원
                r = c.post("/api/auth/login", json={"email": EMAIL, "password": PW1})
                expect(r.status_code == 200, "login w/ rotated password")
                token = r.json()["data"]["accessToken"]
                H = {"Authorization": f"Bearer {token}"}
                # PW0 으로 되돌림
                r = c.put("/api/users/me/password", headers=H,
                          json={"currentPassword": PW1, "newPassword": PW0})
                expect(r.status_code == 200, "rollback password to baseline")
                r = c.post("/api/auth/login", json={"email": EMAIL, "password": PW0})
        expect(r.status_code == 200, f"login/register {r.status_code}")
        token = r.json()["data"]["accessToken"]
        H = {"Authorization": f"Bearer {token}"}

        # GET /users/me
        r = c.get("/api/users/me", headers=H)
        expect(r.status_code == 200, "GET /users/me")
        u = r.json()["data"]["user"]
        expect(u["email"] == EMAIL, "email matches")
        print(f"     baseline displayName={u.get('displayName')!r} role={u['role']}")

        # 표시 이름 변경
        new_name = "프로필 스모크"
        r = c.put("/api/users/me", headers=H, json={"displayName": new_name})
        expect(r.status_code == 200, "PUT /users/me")
        expect(r.json()["data"]["user"]["displayName"] == new_name, "displayName updated")

        # 같은 값 재요청 — 멱등 (변경 없음)
        r = c.put("/api/users/me", headers=H, json={"displayName": new_name})
        expect(r.status_code == 200, "PUT /users/me (idempotent)")
        expect(r.json()["data"]["user"]["displayName"] == new_name, "displayName persisted")

        # 인증 없이 → 401
        r = c.get("/api/users/me")
        expect(r.status_code == 401, f"401 without auth (got {r.status_code})")

        # 비밀번호 변경 — 잘못된 현재 비번 → 401
        r = c.put("/api/users/me/password", headers=H,
                  json={"currentPassword": "wrong", "newPassword": PW1})
        expect(r.status_code == 401, f"401 wrong current password (got {r.status_code})")

        # 새 비번 짧음 → 422
        r = c.put("/api/users/me/password", headers=H,
                  json={"currentPassword": PW0, "newPassword": "abc"})
        expect(r.status_code == 422, f"422 on short password (got {r.status_code})")

        # 같은 비번 → 400
        r = c.put("/api/users/me/password", headers=H,
                  json={"currentPassword": PW0, "newPassword": PW0})
        expect(r.status_code == 400, f"400 same password (got {r.status_code})")

        # 정상 변경
        r = c.put("/api/users/me/password", headers=H,
                  json={"currentPassword": PW0, "newPassword": PW1})
        expect(r.status_code == 200, f"password change OK (got {r.status_code})")

        # 옛 비번으로 로그인 → 401
        r = c.post("/api/auth/login", json={"email": EMAIL, "password": PW0})
        expect(r.status_code == 401, f"old password rejected (got {r.status_code})")

        # 새 비번으로 로그인 → 200
        r = c.post("/api/auth/login", json={"email": EMAIL, "password": PW1})
        expect(r.status_code == 200, "new password accepted")

        # 원복 (다음 실행 영향 최소화)
        token = r.json()["data"]["accessToken"]
        H = {"Authorization": f"Bearer {token}"}
        r = c.put("/api/users/me/password", headers=H,
                  json={"currentPassword": PW1, "newPassword": PW0})
        expect(r.status_code == 200, "rollback password")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
