"""백업/내보내기 (Step 18) 스모크.

검증:
1. 사업 + 첨부 + 댓글 + PPTX 산출물 생성
2. 단일 사업 export → zip 안에 manifest/project/attachments/artifacts/comments 모두 존재
3. summary 엔드포인트 → projectCount 정확
4. 전체 export-all → zip 안에 본인 사업 모두 포함
5. 다른 사용자 → 403
"""
import io
import json
import sys
import zipfile

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
        owner = login(c, "backup-smoke@example.com")
        other = login(c, "backup-other@example.com")
        Ho = {"Authorization": f"Bearer {owner}"}
        Hx = {"Authorization": f"Bearer {other}"}

        # 1) 사업 + 데이터 준비
        r = c.post("/api/projects", headers=Ho, json={"projectName": "백업 사업 A", "goal": "백업 테스트"})
        a_uuid = r.json()["data"]["uuid"]

        # 첨부
        files = [("notice", ("notice.txt", "백업 NOTICE 내용".encode("utf-8"), "text/plain"))]
        r = c.post("/api/files/analyze", headers=Ho, data={"projectUuid": a_uuid}, files=files)
        expect(r.status_code == 200, "upload notice")

        # PPTX
        r = c.post("/api/generate/pptx", headers=Ho, json={"projectUuid": a_uuid})
        expect(r.status_code == 200, "generate PPTX")

        # 댓글
        r = c.post(f"/api/projects/{a_uuid}/comments", headers=Ho, json={"body": "백업 댓글입니다."})
        expect(r.status_code == 200, "add comment")

        # 2) 단일 export
        r = c.get(f"/api/projects/{a_uuid}/export", headers=Ho)
        expect(r.status_code == 200, f"export project ({r.status_code}: {r.text[:200]})")
        expect(r.headers.get("content-type") == "application/zip", "zip content-type")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        expect(any(n == "manifest.json" for n in names), f"manifest in zip ({names})")
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        expect(manifest["exportType"] == "project", "exportType=project")
        expect(manifest["projectUuid"] == a_uuid, "projectUuid in manifest")
        expect(manifest["counts"]["attachments"] >= 1, f"attachment included ({manifest['counts']})")
        expect(manifest["counts"]["artifacts"] >= 1, "artifact included")
        expect(manifest["counts"]["comments"] >= 1, "comment included")

        prefix = f"projects/{a_uuid}"
        expect(any(n == f"{prefix}/project.json" for n in names), "project.json")
        expect(any(n == f"{prefix}/attachments.json" for n in names), "attachments.json")
        expect(any(n == f"{prefix}/artifacts.json" for n in names), "artifacts.json")
        expect(any(n == f"{prefix}/comments.json" for n in names), "comments.json")
        expect(any(n.startswith(f"{prefix}/attachments/") for n in names), "attachment file")
        expect(any(n.startswith(f"{prefix}/artifacts/") for n in names), "artifact file")

        # heuristic fallback 으로 인해 projectName 이 변경되었을 수 있음 — 현재값과 비교
        cur = c.get(f"/api/projects/{a_uuid}", headers=Ho).json()["data"]
        proj = json.loads(zf.read(f"{prefix}/project.json").decode("utf-8"))
        expect(proj["projectName"] == cur["projectName"], f"project name in dump matches current ({proj['projectName']!r} vs {cur['projectName']!r})")

        comments = json.loads(zf.read(f"{prefix}/comments.json").decode("utf-8"))
        expect(any("백업 댓글" in c["body"] for c in comments), "comment text in dump")

        # 3) summary
        r = c.get("/api/me/export-summary", headers=Ho)
        expect(r.status_code == 200, "summary")
        s = r.json()["data"]
        expect(s["projectCount"] >= 1, f"projectCount >= 1 (got {s['projectCount']})")
        expect(any(p["uuid"] == a_uuid for p in s["projects"]), "A in summary")

        # 4) export-all
        r = c.get("/api/me/export-all", headers=Ho)
        expect(r.status_code == 200, "export-all")
        zf2 = zipfile.ZipFile(io.BytesIO(r.content))
        manifest2 = json.loads(zf2.read("manifest.json").decode("utf-8"))
        expect(manifest2["exportType"] == "user", "exportType=user")
        expect(manifest2["projectCount"] >= 1, "projectCount in manifest")
        expect(f"projects/{a_uuid}/project.json" in zf2.namelist(), "A's project.json in user-zip")
        expect("summary.json" in zf2.namelist(), "summary.json in user-zip")

        # 5) 다른 사용자 → 403
        r = c.get(f"/api/projects/{a_uuid}/export", headers=Hx)
        expect(r.status_code == 403, f"403 other user (got {r.status_code})")

        # 정리
        c.delete(f"/api/projects/{a_uuid}", headers=Ho)
        c.delete(f"/api/projects/{a_uuid}/purge", headers=Ho)

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
