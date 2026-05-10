# Lon — 메뉴 구성도 (Menu Structure)

- 문서 버전: v0.1
- 작성일: 2026-05-03
- 관련: `screen-design.md`

---

## 1. 메뉴 트리

```
Lon
├── 1. 홈                                     /                  [USER]
├── 2. 사업제안서 생성                         /generator         [USER]
│    ├── 2.1 신규 생성                        /generator         [USER]
│    └── 2.2 템플릿에서 시작                  /generator?tpl=…   [USER]
├── 3. 사업 관리                              /projects          [USER]
│    ├── 3.1 사업 목록                        /projects          [USER]
│    ├── 3.2 사업 상세                        /projects/:id      [USER]
│    │    ├── 산출물 미리보기                 /projects/:id/preview
│    │    ├── LLM 호출 이력                   /projects/:id/logs
│    │    └── 사업 복제                       (action)
│    └── 3.3 휴지통                           /projects/trash    [USER]
├── 4. 산출물 라이브러리                       /artifacts         [USER]
│    ├── 4.1 PPTX                            /artifacts?type=pptx
│    └── 4.2 XLSX (WBS)                      /artifacts?type=xlsx
├── 5. 설정                                  /settings          [USER]
│    ├── 5.1 AI Provider/Key                /settings/ai
│    ├── 5.2 환경 설정                       /settings/env
│    │    ├── 언어 / 테마 / 자동 저장
│    │    └── 작업 폴더 경로
│    └── 5.3 단축키                          /settings/shortcuts
├── 6. 관리                                  /admin             [ADMIN]
│    ├── 6.1 사용자 관리                     /admin/users
│    ├── 6.2 표준 목차 관리                  /admin/category
│    ├── 6.3 시스템 프롬프트                 /admin/prompts
│    ├── 6.4 감사 로그                       /admin/audit
│    └── 6.5 잡(Job) 모니터                  /admin/jobs
└── 7. 도움말                                /help              [공통]
     ├── 7.1 사용 가이드                     /help/guide
     ├── 7.2 단축키 / FAQ                    /help/faq
     └── 7.3 정보(About)                     /help/about
```

---

## 2. 권한별 노출

| 메뉴 | USER | ADMIN | 비로그인 |
|---|:---:|:---:|:---:|
| 1. 홈 | ✓ | ✓ | – |
| 2. 사업제안서 생성 | ✓ | ✓ | – |
| 3. 사업 관리 | ✓ | ✓ | – |
| 4. 산출물 라이브러리 | ✓ | ✓ | – |
| 5. 설정 | ✓ | ✓ | – |
| 6. 관리 | – | ✓ | – |
| 7. 도움말 | ✓ | ✓ | ✓ |
| 로그인 | – | – | ✓ |

---

## 3. 화면 ↔ 메뉴 매핑

| 메뉴 | 화면 ID | 비고 |
|---|---|---|
| 1. 홈 | S-010 | 대시보드 |
| 2.1 신규 생성 | S-100 | 메인 (이미지 화면) |
| 2.2 템플릿에서 시작 | S-100 | 쿼리 파라미터로 사전 채움 |
| 3.1 사업 목록 | S-110 | |
| 3.2 사업 상세 | S-111 | |
| – 산출물 미리보기 | S-120 | |
| 5.1 AI 키 | S-200 | |
| 5.2 환경 설정 | S-210 | |
| 6.2 표준 목차 | S-300 | |
| 6.1 사용자 관리 | S-310 | |
| 4xx/5xx | S-900 | |

---

## 4. 사이드바 (운영 화면 좌측 네비) UX

```
┌─────────┐
│  Lon    │  ← 로고 / 워크스페이스 선택
├─────────┤
│ 🏠 홈    │
│ ✨ 생성  │
│ 📋 사업  │
│ 📦 산출  │
├─────────┤
│ ⚙ 설정  │
│ 🛡 관리  │  (ADMIN만)
│ ❓ 도움  │
└─────────┘
```

- 동작: 1Depth 클릭 시 본문 영역 전환, 2Depth는 본문 상단 탭으로 노출
- 접힘(collapse) 모드: 아이콘만, 폭 64px
- 활성 표시: 좌측 4px 강조 바

---

## 5. 상단 바 (Top Bar)

| 영역 | 요소 |
|---|---|
| 좌측 | 워크스페이스명, 브레드크럼 |
| 가운데 | 글로벌 검색 (사업명/산출물 통합) |
| 우측 | 알림 🔔, 테마 토글 ☼/☽, 사용자 아바타 ▼ |

- 사용자 ▼ 메뉴: 프로필 / 설정 / 로그아웃

---

## 6. URL 라우팅 규칙

- 동사가 아닌 명사형 자원 명명 (`/projects/:id`)
- 페이지네이션: `?page=&size=&sort=updatedAt,desc`
- 깊은 링크 가능: 사업 상세, 산출물 미리보기 모두 새로고침 안전
- 권한 미달 라우트 접근 → `/error/403`로 리다이렉트

---

## 7. 단축키 (전역)

| 단축키 | 동작 |
|---|---|
| `Ctrl + K` | 글로벌 검색 |
| `Ctrl + N` | 신규 사업제안서 |
| `Ctrl + S` | 현재 사업 정보 저장 |
| `Ctrl + Enter` | 현재 컨텍스트 산출물 생성 (PPTX 우선) |
| `?` | 단축키 도움말 표시 |

---

## 부록 A. 메뉴 카탈로그 JSON (FE 시드)
```json
[
  { "id": "home", "label": "홈", "path": "/", "icon": "home", "role": ["USER","ADMIN"] },
  { "id": "generator", "label": "사업제안서 생성", "path": "/generator", "icon": "sparkles", "role": ["USER","ADMIN"] },
  { "id": "projects", "label": "사업 관리", "path": "/projects", "icon": "folder", "role": ["USER","ADMIN"],
    "children": [
      { "id": "projects.list", "label": "사업 목록", "path": "/projects" },
      { "id": "projects.trash", "label": "휴지통", "path": "/projects/trash" }
    ]
  },
  { "id": "artifacts", "label": "산출물", "path": "/artifacts", "icon": "package", "role": ["USER","ADMIN"] },
  { "id": "settings", "label": "설정", "path": "/settings", "icon": "settings", "role": ["USER","ADMIN"],
    "children": [
      { "id": "settings.ai", "label": "AI Provider/Key", "path": "/settings/ai" },
      { "id": "settings.env", "label": "환경 설정", "path": "/settings/env" }
    ]
  },
  { "id": "admin", "label": "관리", "path": "/admin", "icon": "shield", "role": ["ADMIN"],
    "children": [
      { "id": "admin.users", "label": "사용자 관리", "path": "/admin/users" },
      { "id": "admin.category", "label": "표준 목차", "path": "/admin/category" },
      { "id": "admin.prompts", "label": "시스템 프롬프트", "path": "/admin/prompts" },
      { "id": "admin.audit", "label": "감사 로그", "path": "/admin/audit" },
      { "id": "admin.jobs", "label": "잡 모니터", "path": "/admin/jobs" }
    ]
  },
  { "id": "help", "label": "도움말", "path": "/help", "icon": "help", "role": ["USER","ADMIN","GUEST"] }
]
```
