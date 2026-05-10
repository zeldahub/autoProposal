"""S-200 AI 키 관리 + 자동 사용 스모크 테스트."""
import io
import sys

# Windows cp949 콘솔에서도 유니코드 출력 가능하게
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

BASE = "http://localhost:8089"


def expect(cond, label):
    print(f"  [{'OK' if cond else 'FAIL'}] {label}")
    if not cond:
        sys.exit(1)


def login(c: httpx.Client) -> str:
    r = c.post("/api/auth/register", json={
        "email": "set-smoke@example.com", "password": "secret123",
    })
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": "set-smoke@example.com", "password": "secret123"})
    r.raise_for_status()
    return r.json()["data"]["accessToken"]


def main():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        token = login(c)
        H = {"Authorization": f"Bearer {token}"}

        # 0) 이전 실행 잔재 정리
        for s in c.get("/api/settings/ai", headers=H).json()["data"]["items"]:
            c.delete(f"/api/settings/ai/{s['id']}", headers=H)

        # 1) 초기 상태: active=null
        r = c.get("/api/settings/ai/active", headers=H)
        expect(r.status_code == 200 and r.json()["data"]["setting"] is None, "active=null initially")

        # 2) 등록 (Gemini)
        r = c.post("/api/settings/ai", headers=H, json={
            "provider": "GEMINI", "alias": "회사 공용",
            "apiKey": "AIzaTESTONLY_LONG_FAKE_KEY_FOR_SMOKE",
            "defaultModel": "gemini-2.5-flash",
            "temperature": 0.4, "isActive": True,
        })
        expect(r.status_code == 200, f"create {r.status_code}")
        s = r.json()["data"]
        sid = s["id"]
        expect(s["keyPreview"].startswith("AIza") and "•" in s["keyPreview"], f"masked preview ok")
        expect("TESTONLY" not in s["keyPreview"], "raw key not leaked")

        # 3) 중복 등록 차단
        r = c.post("/api/settings/ai", headers=H, json={
            "provider": "GEMINI", "alias": "회사 공용",
            "apiKey": "AIzaANOTHER_FAKE_LONG_KEY_FOR_DUPLICATE_TEST",
        })
        expect(r.status_code == 409, f"duplicate alias → 409 (got {r.status_code})")

        # 4) 목록
        r = c.get("/api/settings/ai", headers=H)
        items = r.json()["data"]["items"]
        expect(r.status_code == 200 and len(items) == 1, f"list count={len(items)}")
        expect(all("apiKey" not in i for i in items), "no raw apiKey in list response")

        # 5) active 조회
        r = c.get("/api/settings/ai/active", headers=H)
        expect(r.json()["data"]["setting"]["id"] == sid, "active=created")

        # 6) test (가짜 키 → 401)
        r = c.post(f"/api/settings/ai/{sid}/test", headers=H)
        expect(r.status_code == 401 and r.json()["error"]["code"] == "LON-LLM-401", "test → 401")

        # 7) 부분 수정 (비활성화)
        r = c.put(f"/api/settings/ai/{sid}", headers=H, json={"isActive": False})
        expect(r.status_code == 200 and r.json()["data"]["isActive"] is False, "deactivate")

        r = c.get("/api/settings/ai/active", headers=H)
        expect(r.json()["data"]["setting"] is None, "active=null after deactivate")

        # 8) 다시 활성 + 자동 키 사용 검증 (analyze 요청에 키 미포함)
        c.put(f"/api/settings/ai/{sid}", headers=H, json={"isActive": True})

        notice = ("사업명: 자동키 검증 사업\n사업 목표: 키 자동 사용 확인\n").encode("utf-8")
        r = c.post("/api/files/analyze", headers=H,
                   files={"notice": ("n.txt", notice, "text/plain")})
        # 가짜 키이므로 LLM 호출은 실패하지만 라우터는 200 반환 + llm.error 표시
        d = r.json()["data"]
        expect(r.status_code == 200, f"analyze {r.status_code}")
        # 저장된 키 사용을 시도했어야 함 (used=False지만 error 메시지 존재)
        expect(d["llm"]["used"] is False, "llm.used=false (fake key)")
        expect(d["llm"].get("error") is not None, "llm.error present (LLM was attempted)")
        print(f"     llm.error={d['llm']['error'][:80]}...")

        # 9) PPTX 생성: 자동 키 사용 시도 (카테고리당 격리되어 placeholder slide로 마무리)
        uuid = d["projectUuid"]
        r = c.post("/api/generate/pptx", headers=H, json={
            "projectUuid": uuid, "categories": ["OVERVIEW"],
        })
        expect(r.status_code == 200 and r.headers.get("x-llm-used") == "1",
               f"generate.pptx attempted stored key (got {r.status_code}/{r.headers.get('x-llm-used')})")

        # 10) 비활성화 후 재시도 → placeholder 모드 동작 (200)
        c.put(f"/api/settings/ai/{sid}", headers=H, json={"isActive": False})
        r = c.post("/api/generate/pptx", headers=H, json={
            "projectUuid": uuid, "categories": ["OVERVIEW"],
        })
        expect(r.status_code == 200 and r.headers.get("x-llm-used") == "0",
               f"generate.pptx placeholder after deactivate (got {r.status_code}/{r.headers.get('x-llm-used')})")

        # 11) 삭제
        r = c.delete(f"/api/settings/ai/{sid}", headers=H)
        expect(r.status_code == 200, "delete")
        r = c.get("/api/settings/ai", headers=H)
        expect(len(r.json()["data"]["items"]) == 0, "list empty after delete")

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
