# Lon — 화면설계서 (Screen Design Document)

- 문서 버전: v0.1
- 작성일: 2026-05-03
- 관련 문서: `service-plan.md`

---

## 1. 화면 목록

| ID | 화면명 | URL | 설명 | 권한 |
|---|---|---|---|---|
| S-000 | 로그인 | `/login` | 로컬 계정 로그인 (옵션: SSO) | 비회원 |
| S-010 | 홈/대시보드 | `/` | 최근 사업, 산출물 통계 | 사용자 |
| S-100 | 사업제안서 생성기(메인) | `/generator` | 이미지 기준 메인 화면 | 사용자 |
| S-110 | 사업 목록 | `/projects` | 저장된 사업 목록/검색 | 사용자 |
| S-111 | 사업 상세 | `/projects/:id` | 사업 정보 + 산출물 이력 | 사용자 |
| S-120 | 산출물 미리보기 | `/projects/:id/preview` | PPTX/XLSX 미리보기 | 사용자 |
| S-200 | AI 키 관리 | `/settings/ai` | Provider별 키 등록·검증 | 사용자 |
| S-210 | 환경 설정 | `/settings/env` | 언어/테마/저장 경로 | 사용자 |
| S-300 | 표준 목차 관리 | `/admin/category` | 제안서 카테고리 마스터 | 관리자 |
| S-310 | 사용자 관리 | `/admin/users` | 계정/권한 관리 | 관리자 |
| S-900 | 에러/접근 거부 | `/error/:code` | 4xx/5xx 공통 화면 | 공통 |

---

## 2. 공통 영역

### 2.1 레이아웃
```
┌─────────────────────────────────────────────────┐
│  [Top Bar] 로고  사업명  사용자메뉴  알림  테마  │
├──────────┬──────────────────────────────────────┤
│          │                                       │
│  [Side]  │           [Content Area]              │
│  생성기  │                                       │
│  사업    │                                       │
│  설정    │                                       │
│          │                                       │
└──────────┴──────────────────────────────────────┘
                [Footer] © Lon 2026
```

### 2.2 디자인 토큰
| 토큰 | 값 | 용도 |
|---|---|---|
| `--color-bg` | `#0F1623` | 다크 배경 (이미지 톤) |
| `--color-surface` | `#1A2332` | 카드 배경 |
| `--color-primary` | `#3B82F6` | CTA 버튼 |
| `--color-accent` | `#10B981` | 성공/생성 |
| `--color-danger` | `#EF4444` | 에러/Not Found |
| `--radius-md` | `12px` | 카드 라운드 |
| `--font-ko` | 맑은 고딕 | 본문 |

---

## 3. S-100 사업제안서 생성기 (메인) — 이미지 매핑

### 3.1 화면 구성

```
┌─────────────────────────────────────────────────┐
│ ① AI 서비스 선택                                  │
│   [ChatGPT][Gemini✓][Claude]                     │
│   API Key: ••••••••••  Model: [gemini-2.5-flash]│
│   [연결 테스트] [상태 확인]   상태: Not Found     │
├─────────────────────────────────────────────────┤
│ ② 데이터 파일(MD) 분석                            │
│   ┌─사업공고──┐  ┌─관련산출물──┐  [분석 시작]    │
│   │ Drop here │  │ Drop here  │                 │
│   └───────────┘  └────────────┘                 │
├─────────────────────────────────────────────────┤
│ ③ 사업 정보 입력 (12 필드)                       │
│   회사명 [    ]      사업명 [에코드림(ecoDream)] │
│   사업 목표 [textarea]                           │
│   ...                                            │
├─────────────────────────────────────────────────┤
│ ④ 산출 사항 업로드                                │
│   ☑ 사업제안서(PPTX)   ☑ WBS(Excel)              │
│   [사업제안서 PPTX 생성]   [WBS 엑셀 생성]        │
├─────────────────────────────────────────────────┤
│ ⑤ 표준 목차 카테고리 (카드 그리드)                │
│   [사업개요][일반사항][기술요구][사업관리]…       │
└─────────────────────────────────────────────────┘
```

### 3.2 컴포넌트 명세

| 코드 | 컴포넌트 | 타입 | 필수 | 검증 | 이벤트 |
|---|---|---|---|---|---|
| C-101 | `ProviderCard` | 라디오(카드 3개) | Y | 1개 선택 | onChange→상태 초기화 |
| C-102 | `ApiKeyInput` | password input | Y | 길이≥10 | onBlur→마스킹 표시 |
| C-103 | `ModelSelect` | select | Y | provider별 옵션 | onChange |
| C-104 | `BtnTest` | button | - | 키 입력 시 활성 | onClick→`/api/llm/test` |
| C-105 | `BtnStatus` | button | - | - | onClick→상태 폴링 |
| C-106 | `StatusBadge` | label | - | - | OK / Not Found / Error |
| C-201 | `UploadDropzone` ×2 | drag&drop | N | ≤10MB, ext 화이트리스트 | onDrop→사전 검증 |
| C-202 | `BtnAnalyze` | button | - | 첨부 1개 이상 | onClick→`/api/files/analyze` |
| C-301 | `TextField` ×7 | input | 일부 Y | 길이/형식 | onChange→자동 저장 |
| C-302 | `TextArea` ×7 | textarea | 일부 Y | 1000자 | onChange→자동 저장 |
| C-401 | `Checkbox` ×2 | checkbox | - | 1개 이상 | onChange |
| C-402 | `BtnGenPPTX` | button | - | ④ 1개 이상 체크 | onClick→`/api/generate/pptx` |
| C-403 | `BtnGenWBS` | button | - | ④ 1개 이상 체크 | onClick→`/api/generate/wbs` |
| C-501 | `CategoryCard` ×N | card | - | - | onClick→상세 모달 |

### 3.3 상태 머신 (생성 버튼)
```
[idle] ─click→ [validating] ─OK→ [generating] ─done→ [success]
                    │                  │                 │
                    └──fail──→[error]──└─fail→[error]    └─→ download
```

### 3.4 검증 규칙
- 회사명/사업명: 1~80자, 특수문자 `<>` 금지
- API Key: 형식 = provider별 정규식 (예: `sk-` for OpenAI, `AIza` for Gemini)
- 첨부 파일: PDF/DOCX/TXT/MD only, 각 ≤10MB, 합계 ≤30MB
- 추진 예산: 숫자 + 단위 (예: `1,200,000,000원`)

---

## 4. S-110 사업 목록 / S-111 상세

### 4.1 목록 (S-110)
| 컬럼 | 정렬 | 검색 |
|---|---|---|
| 사업명 | ✓ | LIKE |
| 회사명 | ✓ | LIKE |
| AI Provider | ✓ | = |
| 산출물 수 | ✓ | - |
| 수정일 | 기본 DESC | 기간 |

- 페이징: 20건/페이지, 무한 스크롤 옵션
- 액션: [열기] [복제] [삭제(휴지통)]

### 4.2 상세 (S-111) 구성
- 좌측: 사업 정보 카드 (12필드 요약)
- 우측: 산출물 타임라인 (PPTX/XLSX 다운로드, 미리보기, 재생성 버튼)
- 하단: LLM 호출 이력 (입력 토큰/출력 토큰/모델/소요시간)

---

## 5. S-200 AI 키 관리

| 영역 | 필드 |
|---|---|
| Provider 카드 | OpenAI / Gemini / Anthropic |
| Key 등록 | API Key, 별칭, 만료일(옵션) |
| 모델 사전 설정 | 기본 모델 선택, 온도(temperature), max_tokens |
| 사용량 | 호출수/토큰/비용(추정) — 7일/30일 |
| 보안 | OS 키체인 동기화 토글, 키 회전(Rotate) |

---

## 6. S-300 표준 목차 관리 (관리자)

- Tree UI: 대분류(7) → 중분류(N) → 소분류(N)
- 액션: 추가/수정/삭제/순서변경 (드래그)
- 카테고리별: 슬라이드 템플릿 매핑, LLM 시스템 프롬프트 매핑

---

## 7. 사용자 흐름 (User Flow)

### 7.1 신규 제안서 생성
```
S-000 → S-010 → (좌측 메뉴) → S-100
  → ① 키 검증 → ② 첨부 분석 → ③ 폼 보완
  → ④ PPTX 생성 → S-120 미리보기 → 다운로드
```

### 7.2 기존 사업 재활용
```
S-110 검색 → S-111 상세 → [복제] → S-100 (필드 사전 채움)
  → ④ 재생성
```

---

## 8. 반응형 / 접근성

- Breakpoint: ≥1280 (3-col), 768~1279 (2-col), <768 (1-col 스택)
- 키보드 탐색: 모든 폼 Tab 순서 보장, ESC로 모달 닫기
- 명도 대비: WCAG AA, 색상 단독 의미 전달 금지 (배지에 아이콘 병기)
- 한글 폰트 fallback: `'맑은 고딕', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif`

---

## 9. 에러 표시 표준

| 케이스 | UI |
|---|---|
| API 키 무효 | StatusBadge `red`, 토스트 + ApiKeyInput 적색 보더 |
| 파일 초과 | Dropzone 내부 inline 메시지 |
| LLM 타임아웃 | 모달 + 재시도 버튼 |
| 서버 오류(5xx) | S-900으로 라우팅, 코드/추적 ID 표시 |

---

## 부록 A. 와이어프레임 표기

- 본 문서의 ASCII 와이어프레임은 Figma 산출물의 텍스트 대용임
- 실 와이어프레임은 `figma.com/design/<fileKey>/Lon-Generator` 에 게시 (TBD)
