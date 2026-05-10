"""i18n (Step 16) 스모크.

검증:
1. /api/users/me 에 locale 필드 (기본 ko)
2. /api/users/me PUT { locale: 'en' } → locale=en 반영
3. /api/categories?locale=en → name 이 영어
4. /api/categories?locale=ko → name 이 한글
5. invalid locale → 422
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


def main():
    with httpx.Client(base_url=BASE, timeout=60) as c:
        r = c.post("/api/auth/register", json={"email": "i18n-smoke@example.com", "password": "secret123"})
        if r.status_code == 409:
            r = c.post("/api/auth/login", json={"email": "i18n-smoke@example.com", "password": "secret123"})
        token = r.json()["data"]["accessToken"]
        H = {"Authorization": f"Bearer {token}"}

        # 1) GET me — locale 기본 ko
        r = c.get("/api/users/me", headers=H)
        expect(r.status_code == 200, "GET /users/me")
        me = r.json()["data"]["user"]
        expect(me.get("locale") == "ko", f"default locale=ko (got {me.get('locale')})")

        # 2) PUT me locale=en
        r = c.put("/api/users/me", headers=H, json={"locale": "en"})
        expect(r.status_code == 200, f"PUT locale=en ({r.status_code}: {r.text[:200]})")
        body = r.json()["data"]["user"]
        expect(body["locale"] == "en", f"locale=en applied (got {body['locale']})")

        # 다시 GET 으로 확인
        r = c.get("/api/users/me", headers=H)
        expect(r.json()["data"]["user"]["locale"] == "en", "locale persisted")

        # 3) categories?locale=en
        r = c.get("/api/categories", params={"locale": "en"}, headers=H)
        expect(r.status_code == 200, "GET /categories?locale=en")
        items = r.json()["data"]["items"]
        codes_to_name = {x["code"]: x["name"] for x in items}
        # 시드된 OVERVIEW 의 영문명
        expect(codes_to_name.get("OVERVIEW") == "Project Overview",
               f"OVERVIEW name_en (got {codes_to_name.get('OVERVIEW')!r})")
        # nameKo / nameEn 둘 다 응답
        any_with_both = next((x for x in items if x["code"] == "OVERVIEW"), None)
        expect(any_with_both and any_with_both.get("nameKo") and any_with_both.get("nameEn"),
               "both nameKo/nameEn in response")

        # 4) ko 모드
        r = c.get("/api/categories", params={"locale": "ko"}, headers=H)
        items_ko = r.json()["data"]["items"]
        ko_map = {x["code"]: x["name"] for x in items_ko}
        expect(ko_map.get("OVERVIEW") == "사업 개요",
               f"OVERVIEW ko (got {ko_map.get('OVERVIEW')!r})")

        # 5) invalid locale
        r = c.get("/api/categories", params={"locale": "fr"}, headers=H)
        expect(r.status_code == 422, f"invalid locale → 422 (got {r.status_code})")

        # locale fall back to ko 위해 원복
        c.put("/api/users/me", headers=H, json={"locale": "ko"})

    print("\n=== ALL OK ===")


if __name__ == "__main__":
    main()
