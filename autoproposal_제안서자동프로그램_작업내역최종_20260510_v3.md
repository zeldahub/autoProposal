# Lon — AI 사업제안서 자동 생성기 작업 내역 (최종 v3)

**작성일**: 2026-05-10
**프로젝트 경로**: `D:/github/autoProposal/`
**저장소**: https://github.com/zeldahub/autoProposal
**스택**: FastAPI + Vite/React + MariaDB 11.4 + MongoDB 8.x

> 본 문서는 Step 1~13 의 결과물 위에서 진행된 **2026-05-10 통합 작업** 의 최종본입니다.
> v2: Step 14~20 일괄 작업 / v3 초안: 자동화·git·푸시 / **v3 최종(본 문서)**: 운영 매뉴얼 + 로그인 안정화까지 포함.

---

## 0. 한눈에 보기

| 영역 | 항목 | 상태 |
|------|------|------|
| Backend | Step 14 사업 복제 마무리 | ✅ smoke_clone 23/23 |
| Backend | Step 15 PPTX/XLSX 인라인 편집 | ✅ smoke_inline_edit 17/17 |
| Backend/FE | Step 16 다국어 i18n (ko/en) | ✅ smoke_i18n 10/10 |
| Backend/FE | Step 17 사업 협업 (공유+댓글) | ✅ smoke_collaboration 21/21 |
| Backend/FE | Step 18 데이터 백업 (zip) | ✅ smoke_backup 23/23 |
| Infra | Step 19 Docker Compose | ✅ compose 문법 검증 |
| QA | Step 20 단위 테스트 (pytest) | ✅ **35/35** |
| Ops | 자동화 스크립트 4종 | ✅ start/stop/status/deploy |
| Ops | git 구조 정상화 + GitHub 첫 푸시 | ✅ zeldahub/autoProposal main |
| Hotfix | Vite proxy 포트 mismatch (500) | ✅ 8080→8089 |
| Hotfix | 로그인 race condition (세션만료 토스트) | ✅ finishAuth 동기화 |
| Hotfix | reserved TLD `.local` 거부 | ✅ admin@example.com |
| Docs | 운영매뉴얼 (.md + .docx) | ✅ docs/운영매뉴얼.* |

---

## 1. Step 14 — 사업 복제 마무리

기존 `tests/smoke_clone.py` 의 두 가지 이슈를 수정:
1. `b"한글..."` 바이트 리터럴 → `"한글...".encode("utf-8")` 으로 정정
2. `/files/analyze` 의 분석 휴리스틱이 DRAFT 사업의 `goal`/`projectName` 을 덮어쓰는 문제 →
   클론 결과를 **A 의 현재 상태와 비교** 하도록 검증 로직 변경

`smoke_clone.py` **23/23 OK** 확인.

---

## 2. Step 15 — PPTX/XLSX 인라인 편집

**핵심**: 미리보기 좌표(슬라이드#, 시트/행/열)를 그대로 patch 좌표로 사용 → 원본 보존, 다음 version (vN+1) 신규 파일 생성.

### Backend
- **신규 서비스** `app/services/artifact_editor.py`
  - `apply_pptx_edits(src, dst, edits)` — index 별 title/bullets/speakerNote 갱신
  - `apply_xlsx_edits(src, dst, edits)` — sheet/row/col 단일 셀 값 갱신
  - placeholder TITLE 우선 → 없으면 첫 텍스트박스를 title, 다음 박스를 body 로 매핑
- **신규 엔드포인트** `POST /api/artifacts/{id}/edit`
  - body `{ pptxEdits?, xlsxEdits?, note? }`
  - 다음 version 으로 새 파일 + Artifact row + `audit_log(ARTIFACT.EDIT)`
  - 빈 edits → 400, 다른 사용자 → 403

### Frontend
- `ArtifactPreviewDrawer.tsx` 전면 개편
  - 헤더 **편집** 버튼 + **새 버전 저장** / 취소 토글
  - PPTX 편집: 슬라이드별 카드 (title input, bullets textarea, note textarea)
  - XLSX 편집: 시트 탭 + 셀별 inline input
  - 변경 diff 만 서버로 전송, 결과 vN+1 미리보기 자동 로딩
- `client.ts`: `editArtifact(id, body)` 추가

---

## 3. Step 16 — 다국어 지원 (ko/en)

### Backend
- **마이그레이션 V4__i18n.sql**
  - `user.locale VARCHAR(8) NOT NULL DEFAULT 'ko'`
  - `proposal_category.name_en VARCHAR(120)`, `system_prompt_en TEXT`
  - 기본 7개 카테고리 영문명 시드
- 모델: `User.locale`, `ProposalCategory.name_en`, `system_prompt_en`
- 라우터:
  - `GET /api/categories?locale=ko|en` — locale 별 `name` 동적, `nameKo/nameEn` 모두 노출
  - `GET/PUT /api/users/me` 에 `locale` 추가, 잘못된 값 → 422
  - `POST/PUT /api/admin/category` 에 `nameEn / systemPromptEn`

### Frontend
- 자체 경량 i18n (`apps/web/src/i18n/`)
  - `index.tsx` Provider/useT/useI18n + localStorage
  - `ko.ts` / `en.ts` 60+ 키 (공통/네비/로그인/사업/산출물/협업/백업)
  - `{param}` 보간
- `LangToggle` 컴포넌트 → Layout 헤더 우측 KO/EN
- `main.tsx` 에 `<I18nProvider>` 래핑
- Layout NAV 라벨/로그아웃 라벨을 `t()` 로 치환

---

## 4. Step 17 — 사업 협업 (공유 + 댓글)

### Backend
- **마이그레이션 V5__collaboration.sql**
  - `project_share`: `(project_id, user_id) UNIQUE`, `role ENUM('READ','EDIT')`, FK CASCADE
  - `project_comment`: `body TEXT`, `parent_id`, `deleted_at`, project/created 인덱스
- 신규 모델: `ProjectShare`, `ProjectComment` (`app/models/collaboration.py`)
- 신규 라우터: `app/routers/collaboration.py` (prefix `/api`)
  - 공유: `GET/POST/PUT/DELETE /projects/{uuid}/shares[/...]`, `GET /shared-projects`
  - 댓글: `GET/POST /projects/{uuid}/comments`, `DELETE /comments/{id}`
  - 모든 변경에 `audit_log` 기록
- 권한: 공유받은 자 = 사업/댓글 view, 공유 관리(추가/변경/해제) = **소유자/관리자만**
- 댓글 작성 시 사업 소유자에게 자동 알림

### Frontend
- `client.ts` 협업 API 함수
- `components/CollabPanel.tsx` (좌: 공유 / 우: 댓글)
- `ProjectDetail.tsx` 에 **협업** 탭 추가

---

## 5. Step 18 — 데이터 내보내기/백업 (zip)

### Backend
- 신규 서비스 `app/services/backup.py`
  - `build_project_zip(db, mongo, project)` — 단일 사업 zip
  - `build_user_zip(db, mongo, user)` — 본인 소유 모든 사업 zip
- 신규 라우터 `app/routers/backup.py`
  - `GET /api/projects/{uuid}/export` — 단일 사업 zip
  - `GET /api/me/export-all` — 본인 전체 zip
  - `GET /api/me/export-summary` — 미리보기 (사업 수/목록)
  - 한글 파일명 다운로드 → RFC 5987 (`filename*=UTF-8''...`) Content-Disposition
  - `audit_log`: PROJECT.EXPORT / USER.EXPORT_ALL

### zip 구성
```
manifest.json
projects/<uuid>/
  ├── project.json
  ├── attachments.json + attachments/<file>
  ├── artifacts.json + artifacts/<file>
  ├── comments.json
  ├── analysis/latest.json
  └── llm-sessions.jsonl
```

### Frontend
- `client.ts`: `exportProjectZip / exportAllProjectsZip / getExportSummary`
- `ProjectDetail` 헤더 **백업** 버튼
- `Profile` 페이지 **데이터 백업** 카드 + `BackupAllButton`

---

## 6. Step 19 — Docker Compose 패키징

- `docker-compose.yml` 4서비스 (mariadb / mongo / api / web)
- `apps/api/Dockerfile` (Python 3.12-slim + uvicorn 8089) + `.dockerignore`
- `apps/web/Dockerfile` (멀티스테이지: node 빌드 → nginx alpine) + `nginx.conf` + `.dockerignore`
- `infra/mongo-init.js` (lon_app 사용자 + 컬렉션/인덱스)
- `.env.example` (포트/비밀번호/JWT/AES 키)
- `DOCKER.md` (사용 가이드)
- 헬스체크: mariadb / mongo / api / web 각각 정의 + `depends_on: condition: service_healthy`

웹 nginx 가 `/api/*` → api 컨테이너로 프록시 → 브라우저는 8080 단일 진입점.

---

## 7. Step 20 — 단위 테스트 (pytest 35건)

### 구조
- `tests/conftest.py` — apps/api 를 sys.path 에 추가
- `tests/unit/` — 외부 시스템 없이 import 만으로 실행 가능
- `pyproject.toml` `[tool.pytest.ini_options].testpaths = ["tests/unit"]`

### 케이스
| 파일 | 건 | 커버 |
|---|---|---|
| test_security.py | 8 | JWT round-trip / 만료 / 변조, AES-GCM 한글/IV유일성/ciphertext변조/tag변조 |
| test_file_parser.py | 9 | extract_text txt/md/unknown/invalid pdf/docx, chunk_text empty/short/split/blank |
| test_artifact_editor.py | 6 | PPTX title only/bullets only/note/누락 슬라이드, XLSX 셀 갱신/missingSheets |
| test_artifact_preview.py | 4 | PPTX/XLSX preview 기본 + 잘림 |
| test_pptx_builder.py | 3 | placeholder fallback / drafts / WBS xlsx |
| test_backup.py | 5 | _safe_name alphanum/한글/특수문자/길이/언더스코어 |
| **합계** | **35** | **35 passed in ~2s** |

---

## 8. 운영 자동화 스크립트 (`scripts/`)

| 스크립트 | 용도 |
|---|---|
| `start.ps1` | uvicorn 8089 + vite 5173 기동 (별창 또는 `-Background`) |
| `stop.ps1` | 8089/5173 점유 프로세스 정리 + `.lon-pids` 정리 |
| `status.ps1` | 포트/헬스체크/git 상태 한눈에 |
| `deploy.ps1` | auto commit + push (+ 옵션: 브랜치 만들고 PR 자동 머지) |

### `start.ps1`
- 시작 전 8089/5173 점유 PID 자동 정리
- DB(3306)/Mongo(27017) 연결 사전 점검 (실패해도 진행, 경고)
- 기동 후 `/healthz` `/` 헬스체크 결과 표시

### `deploy.ps1`
- 사전: `gh` 가 zeldahub 로 로그인됨, `.git/` 존재, remote 설정
- 변경 없으면 즉시 종료
- 새 브랜치 → `git switch -c`, 기존 → `git switch`
- 커밋 메시지 미지정 시 `chore: auto-deploy yyyy-MM-dd HH:mm`
- `Co-Authored-By` trailer 자동 부착
- 브랜치가 main 이 아니면 `gh pr create` → `gh pr merge --squash --delete-branch --admin` (admin 실패 시 일반 squash 폴백)
- 머지 후 로컬 main 자동 동기화

---

## 9. Git 구조 정상화 + GitHub 첫 푸시

### 이전 비정상 상태
`D:/github/autoProposal/` 루트에 git 내부 파일이 **`.git/` 폴더 없이** 직접 위치:
```
HEAD, config, description, hooks/, info/, objects/, refs/  ← .git/ 폴더 없음
apps/, db/, docs/, ...                                      ← 작업 디렉토리
```
`bare = false` 인데 `.git/` 폴더가 없어 `git status` → `fatal: this operation must be run in a work tree`

### 정리
```bash
mkdir .git
mv HEAD config description hooks info objects refs .git/
```
이제 정상 git 저장소. config 의 `[remote "origin"] url = https://github.com/zeldahub/autoProposal.git` 그대로 보존.

### 첫 커밋 + 푸시
- 작업 디렉토리 전체 `git add -A` → 179개 파일 스테이지
- 커밋 `e433154` — `feat: Step 14~20 일괄 (인라인 편집/i18n/협업/백업/Docker/pytest)`
- `git push -u origin main` → **https://github.com/zeldahub/autoProposal/commits/main**

---

## 10. Hotfix — 로그인 흐름 안정화

### 10-1. Vite proxy 포트 mismatch (Login 500 에러)

**증상**: 로그인 시 "Request failed with status code 500"

**원인**: `apps/web/vite.config.ts` 의 proxy target 이 `http://localhost:8080` 으로 박혀 있는데 실제 API 는 **8089** 에서 동작 → ECONNREFUSED → Vite 가 기본 500 응답

**수정**:
```ts
const API_TARGET = process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8089";

server: {
  proxy: {
    "/api": {
      target: API_TARGET,
      changeOrigin: true,
      configure(proxy) {
        proxy.on("error", (err, _req, res) => {
          if (res && !res.headersSent) {
            res.writeHead(502, { "Content-Type": "application/json" });
          }
          res?.end(JSON.stringify({
            error: { code: "LON-PROXY-502", message: `API 서버 연결 실패: ${err.message}` },
          }));
        });
      },
    },
  },
}
```
백엔드가 잠깐 끊겨도 브라우저에 502 + 명확한 메시지로 응답.

### 10-2. reserved TLD `.local` 거부 (Login 422)

**증상**: `admin@lon.local` 로 로그인 → 422 "value is not a valid email address: ... reserved name"

**원인**: pydantic `EmailStr` 의 email-validator 가 `.local` 등 special-use TLD 를 거부.

**수정**:
- DB 의 `admin@lon.local` 삭제 → **`admin@example.com / admin1234`** (ADMIN) 신규 생성
- `apps/web/src/pages/Login.tsx` 에서 422 의 `detail` 배열을 사람이 읽기 좋게 정리:
  ```ts
  if (Array.isArray(data?.detail)) {
    msg = data.detail.map(d => `${d.loc.slice(1).join('.')}: ${d.msg}`).join(' / ');
  }
  ```
- 401 일 때 한국어 친절 메시지로 대체
- 안내 문구 갱신: ADMIN/USER 두 계정 표시

### 10-3. 로그인 직후 "세션이 만료되었습니다" + 재로그인 화면 반복

**증상**: 로그인 성공 → `/generator` 진입 → 즉시 토스트 "세션이 만료되었습니다" → `/login` 리다이렉트

**근본 원인**: React useEffect 실행 순서 race condition

```
AuthProvider (부모)            Generator (자식)
  ┌──────────┐                  ┌───────────┐
  │ login()  │                  │           │
  │ setToken │────state queue──▶│           │
  │ nav("/g") │                 │           │
  └──────────┘                  └───────────┘
                ↓ React 렌더 ↓
  ┌──────────┐                  ┌───────────┐
  │ render   │                  │ MOUNT     │
  └──────────┘                  └───────────┘
                ↓ effects (자식 → 부모) ↓
                                 ┌───────────┐
                                 │ useEffect │
                                 │ listCats()│  ← 헤더 미설정! 401
                                 └───────────┘
  ┌──────────┐
  │ useEffect│  ← 헤더 설정 (이미 늦음)
  │ headers= │
  └──────────┘
```

자식 useEffect 가 부모 useEffect 보다 **먼저** 실행되는 React 효과 순서로 인해, Generator 의 `listCategories()` / `getActiveAiSetting()` 호출 시점에 `axios.defaults.headers.Authorization` 이 비어 있음 → 401 → 인터셉터가 토스트 + redirect.

**수정** — `apps/web/src/auth/context.tsx` 의 `finishAuth` 동기화:
```ts
const finishAuth = (data) => {
  // setState 보다 먼저 동기적으로 axios + storage 업데이트
  localStorage.setItem(TOKEN_KEY, data.accessToken);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  api.defaults.headers.common["Authorization"] = `Bearer ${data.accessToken}`;
  setToken(data.accessToken);
  setUser(data.user);
};
```
이제 nav() 후 마운트되는 자식이 토큰 부착된 axios 인스턴스를 사용.

추가로 `apps/web/src/api/client.ts` 인터셉터 안전장치:
- `/auth/login`, `/auth/register` 자체의 401(잘못된 비번) → 글로벌 redirect/토큰정리 제외
- 토큰이 애초에 없었던 경우 → 토스트 생략 (race condition 시 무의미한 토스트 방지)
- `/login` 페이지에서 발생한 401 → redirect 생략

---

## 11. 운영 매뉴얼 (`docs/운영매뉴얼.*`)

### 산출물
- **`docs/운영매뉴얼.md`** (23KB)
- **`docs/운영매뉴얼.docx`** (50KB) — `docs/_md_to_docx.py` 로 자동 변환

### 14개 섹션 구성
1. 시스템 개요 — 스택/포트/주요 기능 11가지
2. 사전 요구사항
3. **개발환경 구성** — venv, MariaDB V1~V5, Mongo init, FE npm, .env, admin 생성
4. 일상 운영 — start/stop/status/deploy.ps1
5. Docker Compose 모드
6. **기능별 사용법** — 로그인/AI키/생성/편집/협업/i18n/백업/알림/관리자/휴지통/복제
7. **기동 테스트** — 헬스체크 + pytest 35건 + smoke 9종 + UI 체크리스트 10항목
8. **트러블슈팅** — 10가지 (세션만료/500/422/포트/bcrypt/cp949/한글파일명/...)
9. 디렉토리 구조
10. 자주 쓰는 명령
11. 보안 체크리스트
12. 운영 인계 / 백업
13. 변경 이력
14. 연락 / 지원

`_md_to_docx.py` 의 `TITLES` 딕셔너리에 매뉴얼 항목 추가 → 한 번 실행으로 .docx 자동 생성. 추후 .md 만 수정하면 동일 명령 한 줄로 .docx 재생성.

---

## 12. 신규 / 변경 파일 일람 (전체)

### 백엔드 신규
```
apps/api/
├── Dockerfile
├── .dockerignore
├── app/
│   ├── models/collaboration.py
│   ├── routers/
│   │   ├── backup.py
│   │   └── collaboration.py
│   └── services/
│       ├── artifact_editor.py
│       └── backup.py
└── tests/
    ├── conftest.py
    ├── smoke_inline_edit.py
    ├── smoke_i18n.py
    ├── smoke_collaboration.py
    ├── smoke_backup.py
    └── unit/
        ├── __init__.py
        ├── test_security.py
        ├── test_file_parser.py
        ├── test_artifact_editor.py
        ├── test_artifact_preview.py
        ├── test_pptx_builder.py
        └── test_backup.py
```

### 프론트엔드 신규
```
apps/web/
├── Dockerfile
├── .dockerignore
├── nginx.conf
└── src/
    ├── i18n/
    │   ├── index.tsx
    │   ├── ko.ts
    │   └── en.ts
    └── components/
        ├── CollabPanel.tsx
        └── LangToggle.tsx
```

### 인프라 / DB / 문서 / 자동화
```
docker-compose.yml
.env.example
DOCKER.md
db/mariadb/migration/
├── V4__i18n.sql
└── V5__collaboration.sql
infra/mongo-init.js
scripts/
├── start.ps1
├── stop.ps1
├── status.ps1
└── deploy.ps1
docs/
├── 운영매뉴얼.md          ← v3 hotfix 단계 신규
└── 운영매뉴얼.docx        ← v3 hotfix 단계 신규
.git/                     ← v3 정상화
└── (HEAD/config/objects/refs/hooks/info/description)
```

### 변경된 기존 파일
- `apps/api/app/main.py` — backup/collaboration 라우터 wire-up
- `apps/api/app/models/__init__.py` — 새 모델 export
- `apps/api/app/models/user.py` — `locale` 필드
- `apps/api/app/models/category.py` — `name_en`, `system_prompt_en`
- `apps/api/app/routers/admin.py` — 카테고리 영문 필드
- `apps/api/app/routers/artifacts.py` — `/edit` 엔드포인트
- `apps/api/app/routers/categories.py` — `?locale=` 지원
- `apps/api/app/routers/users.py` — `locale` 필드 동기화
- `apps/api/pyproject.toml` — pytest testpaths/필터
- `apps/web/src/main.tsx` — `<I18nProvider>` 래핑
- `apps/web/src/api/client.ts` — 편집/협업/백업 API + 401 인터셉터 hotfix
- `apps/web/src/auth/context.tsx` — finishAuth 동기화 (race condition fix)
- `apps/web/src/components/Layout.tsx` — i18n 적용 + LangToggle
- `apps/web/src/components/ArtifactPreviewDrawer.tsx` — 편집 모드
- `apps/web/src/pages/ProjectDetail.tsx` — 협업 탭 + 백업 버튼
- `apps/web/src/pages/Profile.tsx` — 전체 백업 카드
- `apps/web/src/pages/Login.tsx` — 422 detail 친화적 메시지 + 안내 문구
- `apps/web/vite.config.ts` — proxy 8080→8089 + ECONNREFUSED 502
- `docs/_md_to_docx.py` — 운영매뉴얼 변환 항목 추가

---

## 13. DB 인스턴스 변경 사항 (적용 완료)

```sql
-- V4 i18n
ALTER TABLE user ADD COLUMN locale VARCHAR(8) NOT NULL DEFAULT 'ko' AFTER display_name;
ALTER TABLE proposal_category ADD COLUMN name_en VARCHAR(120) NULL AFTER name_ko;
ALTER TABLE proposal_category ADD COLUMN system_prompt_en TEXT NULL AFTER system_prompt;
-- 7개 카테고리 영문명 시드

-- V5 협업
CREATE TABLE project_share (...);
CREATE TABLE project_comment (...);
```

`SHOW TABLES;` → 11개 (project_share, project_comment 포함).
`admin@example.com` 계정 INSERT 완료 (UUID 자동 생성).

---

## 14. 회귀 테스트 결과

### pytest unit
```
35 passed in 1.98s
```

### smoke (uvicorn 8089 기동 후)
```
=== smoke_clone ===              ALL OK
=== smoke_inline_edit ===        ALL OK
=== smoke_i18n ===               ALL OK
=== smoke_collaboration ===      ALL OK
=== smoke_backup ===             ALL OK
=== smoke_notifications ===      ALL OK
=== smoke_trash ===              ALL OK
=== smoke_profile ===            ALL OK
=== smoke_artifact_preview ===   ALL OK
```

### 로그인 흐름 (Vite proxy 경유)
```
admin@example.com / admin1234  → HTTP 200  ✅
smoke@example.com / secret123  → HTTP 200  ✅
/auth/me + /categories + /settings/ai/active + /notifications/unread-count + /users/me 동시 호출 → 5/5 200 ✅
```

---

## 15. 서비스 가동 정보

| URL | 용도 |
|---|---|
| **http://localhost:5173** | **사용자 진입점** (Vite dev) |
| http://localhost:8089/docs | API Swagger UI |
| http://localhost:8089/healthz | API 헬스체크 |

### 테스트 계정
| 이메일 | 비밀번호 | 권한 |
|---|---|---|
| **admin@example.com** | **admin1234** | ADMIN |
| smoke@example.com | secret123 | ADMIN (smoke 테스트용) |

> `.local` 등 reserved TLD 는 pydantic EmailStr 가 거부. `@example.com` 등 일반 도메인 사용 필수.

---

## 16. 자주 쓰는 명령

```powershell
# === 일상 ===
.\scripts\start.ps1                  # 기동 (별창)
.\scripts\start.ps1 -Background      # 기동 (백그라운드)
.\scripts\status.ps1                 # 상태
.\scripts\stop.ps1                   # 종료

# === 배포 ===
.\scripts\deploy.ps1                                  # main 직접 푸시
.\scripts\deploy.ps1 -Message "fix: 알림 레이아웃"
.\scripts\deploy.ps1 -Branch feat/edit-toolbar        # PR 자동 생성+머지
.\scripts\deploy.ps1 -DryRun                          # 실제 변경 없이 미리보기

# === 테스트 ===
cd apps\api
.\.venv\Scripts\python.exe -m pytest tests\unit -v    # 단위 35건
.\.venv\Scripts\python.exe tests\smoke_clone.py
.\.venv\Scripts\python.exe tests\smoke_inline_edit.py
# ... smoke_i18n / smoke_collaboration / smoke_backup ...

# === Docker ===
cd D:\github\autoProposal
copy .env.example .env
docker compose up --build -d

# === 매뉴얼 docx 재생성 ===
cd D:\github\autoProposal
apps\api\.venv\Scripts\python.exe docs\_md_to_docx.py
```

---

## 17. 보류 / 후속 과제

- **i18n 심화**: 산출물(PPTX/XLSX) 빌더의 헤더/카테고리 명을 user.locale 에 따라 동적 (현재 ko 고정)
- **공유받은 사업 페이지**: FE 에서 `/shared-projects` 표시하는 별도 페이지/메뉴 (backend 만 구현)
- **댓글 스레드 트리**: parent_id 컬럼 존재, FE 트리 표시 미구현 (단일 평면 리스트)
- **Docker 실제 빌드 검증**: `docker compose up --build` 사용자 환경 필요 (Docker Desktop)
- **백업 복구(import)**: 현재는 export 만, zip → 사업 재구성 import 미구현
- **Coverage 측정**: pytest-cov 미도입 (현재 35 케이스로 핵심 보안/서비스 커버)
- **CI**: GitHub Actions workflow 미구성 (deploy.ps1 로 로컬 자동화 가능, PR 자동 검증 추가 권장)
- **CRLF/LF**: 첫 푸시 시 다수의 변환 경고. `.gitattributes` 명시 권장
- **로그아웃 후 로그인 토큰 재발급**: `/auth/refresh` 가 `"TODO"` 문자열만 반환 — 향후 refresh 토큰 도입

---

## 18. GitHub 커밋 이력 (2026-05-10)

| 커밋 | 메시지 | 비고 |
|---|---|---|
| `e433154` | feat: Step 14~20 일괄 (인라인 편집/i18n/협업/백업/Docker/pytest) | 첫 커밋, 179 파일 |
| `b3e5625` | docs: 운영매뉴얼 추가 + 로그인 race condition / Vite proxy 수정 | 운영매뉴얼 + 로그인 hotfix |

저장소: https://github.com/zeldahub/autoProposal/commits/main

---

**최종 v3 작업 종료** — Step 14~20 + 자동화 + git 정상화 + GitHub 푸시 + 운영매뉴얼 + 로그인 안정화.
다음 세션에서는 §17 보류 과제 또는 Step 21 신규 기능부터 진행 가능.
