# Lon — AI 사업제안서 자동 생성기 작업 내역 (v2)

**작성일**: 2026-05-10
**프로젝트 경로**: `D:/github/autoProposal/`
**스택**: FastAPI + Vite/React + MariaDB 11.4 + MongoDB 8.x
**대상 단계**: Step 14 마무리 + Step 15 ~ 20 일괄 작업

---

## 0. 한눈에 보기

| Step | 이름 | 상태 | smoke / unit |
|------|---|---|---|
| 14 | 사업 복제 / 템플릿화 (마무리) | ✅ | smoke_clone — 23/23 OK |
| 15 | PPTX/XLSX 인라인 편집 | ✅ | smoke_inline_edit — 17/17 OK |
| 16 | 다국어 지원 i18n (ko/en) | ✅ | smoke_i18n — 10/10 OK |
| 17 | 사업 협업 (공유 + 댓글) | ✅ | smoke_collaboration — 21/21 OK |
| 18 | 데이터 내보내기/백업 (zip) | ✅ | smoke_backup — 23/23 OK |
| 19 | Docker Compose 패키징 | ✅ | compose syntax OK |
| 20 | 단위 테스트 커버리지 강화 | ✅ | pytest — **35/35 OK** |

---

## 1. Step 14 마무리

기존 `tests/smoke_clone.py` 의 두 가지 이슈를 수정:
1. `b"한글..."` 바이트 리터럴 → `"한글...".encode("utf-8")` 으로 정정
2. `/files/analyze` 의 분석 휴리스틱이 DRAFT 사업의 `goal`/`projectName` 을 덮어쓰는 문제 →
   클론 결과를 **A 의 현재 상태와 비교** 하도록 검증 로직 변경

`smoke_clone.py` **23/23 OK** 확인 완료.

---

## 2. Step 15 — PPTX/XLSX 인라인 편집

**핵심 아이디어**: 미리보기에서 사용한 좌표(슬라이드 #, 시트/행/열)를 그대로 patch 좌표로 사용하여,
원본을 보존한 채 **다음 version (vN+1)** 으로 새 산출물 파일을 생성.

### 백엔드
- **신규 서비스**: `app/services/artifact_editor.py`
  - `apply_pptx_edits(src, dst, edits)` — index 별 title/bullets/speakerNote 갱신
  - `apply_xlsx_edits(src, dst, edits)` — sheet/row/col 단일 셀 값 갱신
  - 미리보기 기준 placeholder TITLE 우선 → 없으면 첫 텍스트박스를 title, 다음 박스를 body 로 매핑
- **신규 엔드포인트**: `POST /api/artifacts/{id}/edit`
  - body: `{ pptxEdits?: [...], xlsxEdits?: [...], note?: string }`
  - 다음 version 으로 새 파일을 disk 에 저장 + Artifact row 추가
  - `audit_log(ARTIFACT.EDIT)`, `meta_json` 에 `applied` (반영된 항목 수) 기록
  - 빈 edits → 400, 다른 사용자 → 403

### 프론트엔드
- `ArtifactPreviewDrawer.tsx` 전면 개편
  - 헤더에 **편집** 버튼 + **새 버전 저장** / 취소 토글
  - PPTX 편집 뷰: 슬라이드별 카드 (title input, bullets textarea, note textarea)
  - XLSX 편집 뷰: 시트 탭 + 셀별 inline input
  - 변경 diff 만 서버로 전송 → 결과의 v(N+1) 미리보기를 다시 로딩
- `client.ts`: `editArtifact(id, body)` 추가

### smoke_inline_edit
- v2 생성/version 증가, title/bullet/note 반영 확인
- XLSX 셀 변경 후 재미리보기에서 값 검증
- 권한(403) / 빈 edits(400) 검증

---

## 3. Step 16 — 다국어 지원 (ko/en)

### 백엔드
- **마이그레이션 V4__i18n.sql**:
  - `user.locale VARCHAR(8) NOT NULL DEFAULT 'ko'`
  - `proposal_category.name_en VARCHAR(120)`, `system_prompt_en TEXT`
  - 기본 7개 카테고리에 영문명 시드
- **모델**: `User.locale`, `ProposalCategory.name_en`, `system_prompt_en`
- **라우터 변경**:
  - `GET /api/categories?locale=ko|en` — locale 에 따라 `name` 동적 선택, `nameKo/nameEn` 모두 노출
  - `GET /api/users/me` 응답에 `locale` 추가
  - `PUT /api/users/me` `{ locale: 'ko'|'en' }` 지원, 잘못된 값은 422
  - `POST/PUT /api/admin/category` 에 `nameEn / systemPromptEn` 필드 추가

### 프론트엔드
- 자체 경량 i18n 컨텍스트 (`apps/web/src/i18n/`)
  - `index.tsx` (Provider/useT/useI18n, localStorage 저장)
  - `ko.ts` / `en.ts` (60+ 키, 공통/네비/로그인/사업/산출물/협업/백업)
  - `{param}` 템플릿 보간 지원
- `LangToggle` 컴포넌트 → Layout 헤더 우측에 KO/EN 토글
- `main.tsx` 에 `<I18nProvider>` 래핑
- `Layout.tsx` 의 NAV 라벨/로그아웃 라벨을 `t()` 로 치환

### smoke_i18n
10개 케이스 모두 OK — 기본 ko, locale 변경, 카테고리 영문명, 잘못된 locale 422.

---

## 4. Step 17 — 사업 협업 (공유 + 댓글)

### 백엔드
- **마이그레이션 V5__collaboration.sql**:
  - `project_share`: `(project_id, user_id) UNIQUE`, `role ENUM('READ','EDIT')`, FK CASCADE
  - `project_comment`: `body TEXT`, `parent_id`, `deleted_at`, project/created 인덱스
- **신규 모델**: `ProjectShare`, `ProjectComment` (in `app/models/collaboration.py`)
- **신규 라우터**: `app/routers/collaboration.py` (prefix `/api`)
  - 공유:
    - `GET    /projects/{uuid}/shares`
    - `POST   /projects/{uuid}/shares` (email + role; 이미 있으면 role 갱신, 본인 공유 시 409)
    - `PUT    /projects/{uuid}/shares/{id}` (role 변경)
    - `DELETE /projects/{uuid}/shares/{id}`
    - `GET    /shared-projects` (본인이 공유받은 사업 목록)
  - 댓글:
    - `GET    /projects/{uuid}/comments`
    - `POST   /projects/{uuid}/comments` (작성 시 owner 에게 알림)
    - `DELETE /projects/{uuid}/comments/{id}` (작성자/소유자/관리자만)
- 공유 추가/변경/해제 + 댓글 작성/삭제 모두 `audit_log` 기록
- **권한 모델**: 공유받은 사용자도 `_resolve_project_for_view` 를 통해 사업/댓글 접근 가능,
  공유 관리(추가/변경/해제) 는 **소유자/관리자만** 가능

### 프론트엔드
- `client.ts` 에 협업 API 함수 추가
- `components/CollabPanel.tsx` (좌: 공유 패널 / 우: 댓글 패널)
  - 이메일 추가, role 변경(드롭다운), 해제(확인 모달)
  - 댓글 입력/삭제, 작성자 표시, 시간 포맷
- `ProjectDetail.tsx` 탭에 **협업** 탭 추가 (`tab === "collab"`)

### smoke_collaboration
21개 케이스 모두 OK — 공유 추가/upsert/role 변경/해제, shared-projects 노출, 비공유자 403,
미존재 이메일 404, self-share 409, 댓글로 owner 에게 알림 수신.

---

## 5. Step 18 — 데이터 내보내기/백업 (zip)

### 백엔드
- **신규 서비스**: `app/services/backup.py`
  - `build_project_zip(db, mongo, project)` — 단일 사업 zip
  - `build_user_zip(db, mongo, user)` — 본인 소유 모든 사업 zip
  - 항목별 dump:
    - `manifest.json` (export type, 시각, counts)
    - `projects/<uuid>/project.json` — 사업 메타
    - `projects/<uuid>/attachments.json` + `attachments/<file>` (디스크에서 복사)
    - `projects/<uuid>/artifacts.json` + `artifacts/<file>`
    - `projects/<uuid>/comments.json`
    - `projects/<uuid>/analysis/latest.json` (Mongo)
    - `projects/<uuid>/llm-sessions.jsonl` (Mongo)
- **신규 라우터**: `app/routers/backup.py`
  - `GET /api/projects/{uuid}/export` — 단일 사업 zip
  - `GET /api/me/export-all` — 본인 전체 zip
  - `GET /api/me/export-summary` — 미리보기 (사업 수/목록)
  - 한글 파일명 다운로드를 위해 RFC 5987 (`filename*=UTF-8''...`) Content-Disposition 사용
  - `audit_log`: PROJECT.EXPORT / USER.EXPORT_ALL

### 프론트엔드
- `client.ts`: `exportProjectZip / exportAllProjectsZip / getExportSummary`
- `ProjectDetail` 헤더에 **백업** 버튼 (사업 1건 zip)
- `Profile` 페이지에 "**데이터 백업**" 카드 + `BackupAllButton`
  - 진입 시 export-summary 로 사업 수 표시
  - 클릭 시 zip 다운로드 (파일명 `lon-backup-<ts>.zip`)

### smoke_backup
23개 케이스 모두 OK — manifest/구성 파일 존재, attachments/artifacts/comments 디스크 파일 포함,
project name 일치, summary 정확, export-all zip 구조, 다른 사용자 403.

---

## 6. Step 19 — Docker Compose 패키징

### 산출물
- `docker-compose.yml` (서비스 4개)
  - **mariadb** (11.4): `db/mariadb/migration/*.sql` 을 `/docker-entrypoint-initdb.d` 로 마운트하여 자동 초기화
  - **mongo** (8.0): `infra/mongo-init.js` 로 `lon_app` 사용자/컬렉션/인덱스 셋업
  - **api**: `apps/api/Dockerfile` (Python 3.12-slim + uvicorn 8089), `/data/workspace` 볼륨
  - **web**: `apps/web/Dockerfile` (멀티스테이지: node 빌드 → nginx alpine), `/api/*` → api 컨테이너 프록시
- `apps/api/Dockerfile` + `.dockerignore`
- `apps/web/Dockerfile` + `.dockerignore` + `nginx.conf`
- `infra/mongo-init.js` (lon_app 사용자/인덱스)
- `.env.example` (포트/비밀번호/JWT/AES 키)
- `DOCKER.md` (사용 가이드, init 동작, 트러블슈팅)

### 헬스체크
- mariadb: `healthcheck.sh --connect --innodb_initialized`
- mongo: `db.adminCommand('ping')`
- api: `curl /healthz`
- web: `wget /healthz` (nginx 가 200 응답)
- depends_on + condition: service_healthy 로 기동 순서 보장

---

## 7. Step 20 — 단위 테스트 커버리지 강화 (pytest)

### 구조
- `tests/conftest.py` — apps/api 를 sys.path 에 추가
- `tests/unit/` — 외부 시스템(DB/Mongo) 없이 import 만으로 실행 가능
- `pyproject.toml` `[tool.pytest.ini_options].testpaths = ["tests/unit"]`

### 추가된 테스트 파일 / 케이스 (총 35건)

**test_security.py — 8건**
- JWT round-trip / 만료 / 서명 변조
- AES-GCM ASCII / 한글 / IV 유일성 / ciphertext 변조 / tag 변조

**test_file_parser.py — 9건**
- extract_text: txt / md / unknown ext / invalid pdf / invalid docx
- chunk_text: empty / short / split by size / strips blank paragraphs

**test_artifact_editor.py — 6건**
- PPTX: title only / bullets only / speaker note / 누락 슬라이드 무시
- XLSX: 셀 값 갱신 + 다른 시트 보존 / 미존재 시트 missingSheets 리포트

**test_artifact_preview.py — 4건**
- PPTX preview 기본 + max_slides 제한
- XLSX preview 기본 + 행 잘림 (truncation)

**test_pptx_builder.py — 3건**
- placeholder fallback (title slide + 카테고리), drafts 모드, WBS XLSX 빌더

**test_backup.py — 5건**
- _safe_name: alphanumeric / 한글 / 특수문자 치환 / 길이 절단 / 언더스코어 보존

### 실행
```bash
cd apps/api
.venv/Scripts/python.exe -m pytest tests/unit -v
# ============== 35 passed in 1.98s ==============
```

---

## 8. 신규 파일 일람

### 백엔드
```
apps/api/
├── Dockerfile
├── .dockerignore
├── app/
│   ├── models/collaboration.py          (신규)
│   ├── routers/
│   │   ├── backup.py                    (신규)
│   │   └── collaboration.py             (신규)
│   └── services/
│       ├── artifact_editor.py           (신규)
│       └── backup.py                    (신규)
└── tests/
    ├── conftest.py                      (신규)
    ├── smoke_inline_edit.py             (신규)
    ├── smoke_i18n.py                    (신규)
    ├── smoke_collaboration.py           (신규)
    ├── smoke_backup.py                  (신규)
    └── unit/
        ├── __init__.py
        ├── test_security.py
        ├── test_file_parser.py
        ├── test_artifact_editor.py
        ├── test_artifact_preview.py
        ├── test_pptx_builder.py
        └── test_backup.py
```

### 프론트엔드
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
        ├── CollabPanel.tsx              (신규)
        └── LangToggle.tsx               (신규)
```

### 인프라 / DB / 문서
```
docker-compose.yml
.env.example
DOCKER.md
db/mariadb/migration/
├── V4__i18n.sql                         (신규)
└── V5__collaboration.sql                (신규)
infra/
└── mongo-init.js                        (신규)
```

---

## 9. 변경된 기존 파일

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
- `apps/web/src/api/client.ts` — 편집/협업/백업 API 함수
- `apps/web/src/components/Layout.tsx` — i18n 적용 + LangToggle
- `apps/web/src/components/ArtifactPreviewDrawer.tsx` — 편집 모드 추가
- `apps/web/src/pages/ProjectDetail.tsx` — 협업 탭 + 백업 버튼
- `apps/web/src/pages/Profile.tsx` — 전체 백업 카드

---

## 10. DB 인스턴스 변경 사항 (적용 완료)

```sql
-- V4 (직접 ALTER 로 적용 — DB 인스턴스 반영 완료)
ALTER TABLE user ADD COLUMN locale VARCHAR(8) NOT NULL DEFAULT 'ko' AFTER display_name;
ALTER TABLE proposal_category ADD COLUMN name_en VARCHAR(120) NULL AFTER name_ko;
ALTER TABLE proposal_category ADD COLUMN system_prompt_en TEXT NULL AFTER system_prompt;
-- 7개 카테고리 영문명 시드

-- V5 (적용 완료)
CREATE TABLE project_share (...);
CREATE TABLE project_comment (...);
```

`SHOW TABLES;` 결과에 `project_share`, `project_comment` 추가됨 (총 11개 테이블).

---

## 11. 회귀 테스트 결과

uvicorn 8089 기동 후 9개 smoke 모두 통과:

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

pytest unit:
```
35 passed in 1.98s
```

---

## 12. 보류 / 후속 과제

- **i18n 심화**: 산출물(PPTX/XLSX) 빌더의 헤더/카테고리 명을 user.locale 에 따라 동적 선택 (현재는 ko 고정)
- **공유받은 사업 페이지**: FE 에서 `/shared-projects` 를 표시하는 별도 페이지/메뉴 추가 (라우트는 backend 만 만들어둠)
- **댓글 스레드**: parent_id 컬럼은 만들었지만 FE 트리 표시는 미구현 (단일 평면 리스트)
- **Docker 빌드 검증**: `docker compose up --build` 실제 실행은 사용자 환경(Docker Desktop) 필요 — `docker-compose.yml` 문법은 PyYAML 로 검증됨
- **백업 복구(import)**: 현재는 export 만 지원 (zip → 사업 재구성 import 는 미구현)
- **Coverage 측정**: pytest-cov 도입은 보류 (현재는 35 케이스로 핵심 서비스/보안 커버)

---

## 13. 자주 쓰는 명령

```powershell
# API 기동
cd D:/github/autoProposal/apps/api
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8089 --log-level warning

# unit 테스트
.venv/Scripts/python.exe -m pytest tests/unit -v

# 개별 smoke
.venv/Scripts/python.exe tests/smoke_inline_edit.py
.venv/Scripts/python.exe tests/smoke_i18n.py
.venv/Scripts/python.exe tests/smoke_collaboration.py
.venv/Scripts/python.exe tests/smoke_backup.py

# Docker (Docker Desktop 필요)
cd D:/github/autoProposal
cp .env.example .env
docker compose up --build -d

# 포트 정리
Get-NetTCPConnection -LocalPort 8089 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
```

---

**Step 14~20 일괄 작업 완료** — 신규 smoke 4종 + unit 35건 + 회귀 9종 모두 통과.
