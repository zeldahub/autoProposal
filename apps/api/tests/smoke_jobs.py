"""APScheduler 잡 + admin/jobs 라우트 스모크 테스트."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

BASE = "http://localhost:8089"
ADMIN = "smoke@example.com"
USER = "smoke-llm@example.com"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c, email):
    r = c.post("/api/auth/login", json={"email": email, "password": "secret123"})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        admin_h = {"Authorization": f"Bearer {login(c, ADMIN)}"}
        user_h = {"Authorization": f"Bearer {login(c, USER)}"}

        # 1) USER → 403
        r = c.get("/api/admin/jobs", headers=user_h)
        expect(r.status_code == 403, f"USER → /admin/jobs = 403 (got {r.status_code})")

        # 2) ADMIN list
        r = c.get("/api/admin/jobs", headers=admin_h)
        items = r.json()["data"]["items"]
        ids = [j["id"] for j in items]
        expect(r.status_code == 200, "list 200")
        expect("attachment-cleanup" in ids and "mongo-repair" in ids, f"jobs registered (got {ids})")
        for j in items:
            print(f"     • {j['id']:25} interval={j['intervalMin']}m next={j['nextRunAt']}")

        # 3) 즉시 실행 — mongo-repair
        r = c.post("/api/admin/jobs/mongo-repair/run", headers=admin_h)
        expect(r.status_code == 200, f"run mongo-repair {r.status_code} body={r.text[:200] if r.status_code != 200 else ''}")
        last = r.json()["data"]["lastRun"]
        expect(last["status"] == "OK", f"OK status (got {last['status']}) error={last.get('error')}")
        expect(last["durationMs"] is not None, "duration captured")
        print(f"     mongo-repair result={last['result']}")

        # 4) 즉시 실행 — attachment-cleanup
        r = c.post("/api/admin/jobs/attachment-cleanup/run", headers=admin_h)
        last = r.json()["data"]["lastRun"]
        expect(r.status_code == 200 and last["status"] == "OK", "attachment-cleanup OK")
        print(f"     attachment-cleanup result={last['result']}")

        # 5) 이력 누적 확인
        r = c.get("/api/admin/jobs", headers=admin_h)
        items = {j["id"]: j for j in r.json()["data"]["items"]}
        expect(len(items["mongo-repair"]["history"]) >= 1, "mongo-repair history >=1")
        expect(len(items["attachment-cleanup"]["history"]) >= 1, "attachment-cleanup history >=1")

        # 6) 일시정지
        r = c.put("/api/admin/jobs/mongo-repair/pause", headers=admin_h)
        expect(r.status_code == 200 and r.json()["data"]["paused"] is True, "pause")

        r = c.get("/api/admin/jobs", headers=admin_h)
        mr = next(j for j in r.json()["data"]["items"] if j["id"] == "mongo-repair")
        expect(mr["paused"] is True, "list shows paused=True")

        # 7) 재개
        r = c.put("/api/admin/jobs/mongo-repair/resume", headers=admin_h)
        expect(r.status_code == 200 and r.json()["data"]["paused"] is False, "resume")

        # 8) 없는 잡
        r = c.post("/api/admin/jobs/no-such-job/run", headers=admin_h)
        expect(r.status_code == 404, f"unknown job 404 (got {r.status_code})")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
