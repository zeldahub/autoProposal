# Lon — AI 사업제안서 자동 생성기 서비스 기획서

> 사업공고 및 관련 산출물(MD/PDF/DOCX)을 업로드하고 사업 정보를 입력하면, 생성형 AI(ChatGPT / Google Gemini / Claude)를 활용해 **사업제안서(PPTX)** 와 **WBS(Excel)** 를 자동 생성해 주는 도구.

- 문서 버전: v0.1 (초안)
- 작성일: 2026-05-03
- 산출물 위치: `d:/github/autoProposal/docs/service-plan.md`

---

## 1. 서비스 개요

### 1.1 서비스명
- **국문**: 론(Lon) — AI 사업제안서 자동 생성기
- **영문**: Lon — AI Auto Proposal Generator

### 1.2 한 줄 정의
SI/SM 사업 수주 단계에서 반복적으로 수행되는 **사업제안서 작성** 과 **WBS 수립** 업무를, 공고문·요건 정의서·과거 산출물 등 비정형 문서를 LLM에 컨텍스트로 주입하여 **수 분 내에 초안화**해 주는 데스크톱/웹 도구.

### 1.3 추진 배경
| 구분 | 내용 |
|---|---|
| 문제 | 제안서 1건당 평균 3~5인일 소요, 공고문 분석·목차 구성·문구 정제에 비효율 발생 |
| 기회 | 2024~ 생성형 AI(LLM) API 보편화, 멀티모달 문서 이해 능력 향상 |
| 차별점 | 단일 LLM 종속이 아닌 **ChatGPT / Gemini / Claude 멀티 백엔드** 지원, 사용자 API 키 BYOK(Bring-Your-Own-Key) 방식 |

### 1.4 목표
- (정량) 제안서 초안 작성 시간 **3일 → 30분 이내** 단축
- (정량) WBS 작업 항목 자동 도출 **80건 이상**
- (정성) 한국 공공/민간 SI 표준 목차(사업개요, 일반사항, 기술요구사항, 사업관리, 보안, 제약조건 등) 자동 매핑

---

## 2. 사용자 정의 (Persona)

| 페르소나 | 설명 | 핵심 니즈 |
|---|---|---|
| P1. SI 제안 PM | 입찰 마감 임박, 공고문 100p 분석 필요 | 빠른 초안, 표준 목차 |
| P2. 영업/사전영업 | 비기술자, 빠르게 견적 + 제안서 발송 | 클릭 몇 번으로 PPTX |
| P3. PMO/관리자 | 수주 후 WBS 즉시 작성 필요 | 제안 내용 → WBS 자동 분해 |

---

## 3. 주요 기능 (이미지 분석 기반)

### 3.1 기능 구성도

```
[1] AI 서비스 선택      ─┐
[2] MD 데이터 파일 분석  ─┼─→  [LLM 호출]  ─→  [3] 사업 정보 자동/수동 입력
[3] 사업 정보 입력      ─┘                              │
                                                       ↓
                                          [4] 산출물 생성 (PPTX / XLSX)
```

### 3.2 기능 명세

#### F1. AI 서비스 선택 (이미지 ① 영역)
| 항목 | 상세 |
|---|---|
| 지원 AI | ChatGPT (OpenAI), **Google Gemini (기본)**, Claude (Anthropic) |
| 입력 | API Key (마스킹 입력), 모델 선택 (예: `gemini-2.5-flash`) |
| 검증 | `[연결 테스트]` 버튼 → 1회 토큰 호출하여 200/4xx 판정 |
| 상태 | `[상태 확인]` 버튼 → 키 유효성/쿼터/지연시간 표시. 실패 시 "Not Found" 표기 |
| 저장 | 키는 OS 키체인 또는 AES-256 암호화 후 로컬 저장 (서버 미전송) |

#### F2. 데이터 파일(MD) 분석 (이미지 ② 영역)
| 항목 | 상세 |
|---|---|
| 업로드 슬롯 | (a) 사업공고(공고문)  (b) 관련 산출물 |
| 허용 포맷 | PDF / DOCX / TXT / MD (각 ≤ 10MB) |
| 처리 | 텍스트 추출 → 토큰 청크 분할 → 임베딩 또는 컨텍스트 직접 주입 |
| `[분석 시작]` | LLM에 공고문 요약 + 핵심 요건 추출 → 아래 **F3 폼 자동 채움** |

#### F3. 사업 정보 입력 (이미지 ③ 영역)
| 필드 | 타입 | 비고 |
|---|---|---|
| 회사명 | text | 자사 정보 |
| 사업명 | text | 예: `에코드림 (ecoDream)` |
| 사업 목표 | textarea | F2 결과로 사전 채움 |
| 사업의 범위 | textarea | |
| 사업 추진 일정 | textarea | WBS 자동 생성에 사용 |
| 사업수행 조직 | textarea | |
| 사업수행 인력 | textarea | |
| 소요 비용(개발) | textarea | 참고 라이선스(JIRA, Confluence, JBOSS EAP/EWS 등) 자동 표기 |
| 소요 비용(운영) | textarea | |
| 인지/요금제(라이선스) | textarea | |
| 가용성(지원 가능 시간) | textarea | |
| 추진 예산 | text | 숫자 + 단위 |

#### F4. 산출물 업로드/생성 (이미지 ④ 영역)
| 산출물 | 포맷 | 옵션 | 동작 |
|---|---|---|---|
| 사업제안서 | **PPTX** | 체크박스 | `[사업제안서 PPTX 생성]` 클릭 시 LLM이 표준 목차에 맞춰 슬라이드 작성 |
| WBS 관리표 | **XLSX** | 체크박스 | `[WBS 엑셀 생성]` 클릭 시 일정+범위로 작업 분해 (Phase / Task / 담당 / 산출물 / Dur.) |

#### F5. 사업제안서 항목 카테고리 (이미지 ⑤ 영역)
표준 목차를 카드형 UI로 시각화, 각 카드에 포함될 본문 미리보기/편집 제공.
- 사업 개요 / 일반 사항 / 기술 요구사항 / 사업관리 요구사항 / 보안 요구사항 / 제약 조건 / 기타

---

## 4. 사용자 시나리오

### 4.1 Happy Path (PM 사용)
1. 앱 실행 → AI 서비스 **Gemini** 선택, API Key 입력 → `[연결 테스트]` ✅
2. 공고문 PDF 업로드(슬롯 a), 과거 유사 제안서 MD 업로드(슬롯 b)
3. `[분석 시작]` → 사업명/목표/범위/일정 등 자동 채움
4. 비용/조직/인력 보완 입력
5. **[사업제안서 PPTX 생성]** → 7~10초 후 다운로드
6. **[WBS 엑셀 생성]** → 작업 80건 + 일정 자동 분해

### 4.2 Edge Case
- API Key 무효 → 토스트 + `[상태 확인]` 결과 영역에 사유 표기
- 첨부 10MB 초과 → 업로드 사전 차단
- LLM 토큰 초과 → 자동 청크 분할, 사용자에게 진행률 노출

---

## 5. 시스템 아키텍처(권장)

```
┌────────────────────┐         ┌────────────────────────────┐
│   Frontend (Web)   │  HTTPS  │      Backend (FastAPI)      │
│  Next.js + Tailwind│ ───────►│  - 파일 파싱(pdfminer/docx) │
│  (이미지 디자인)    │         │  - LLM 라우터(OpenAI/Gemini/│
└────────────────────┘         │    Anthropic)              │
        │                      │  - 템플릿 엔진(pptx/xlsx)   │
        │ Local Storage        └──────────┬─────────────────┘
        ▼                                 │
   API Key (암호화)                       ▼
                                  ┌────────────────┐
                                  │  LLM Provider  │
                                  │ (BYOK, 사용자키)│
                                  └────────────────┘
```

- **Stateless**: 사용자 데이터/키는 서버 영구 저장하지 않음(메모리/세션만)
- **Provider 추상화**: `LLMClient` 인터페이스 → 3사 어댑터 구현
- **산출물 생성기**: `python-pptx`, `openpyxl` 사용

---

## 6. 기술 스택

| 레이어 | 채택 | 사유 |
|---|---|---|
| FE | Next.js 14 + Tailwind | 이미지 디자인의 다크/카드 UI 재현 용이 |
| BE | FastAPI (Python 3.12) | LLM SDK·문서 파싱 라이브러리 풍부 |
| LLM SDK | `openai`, `google-genai`, `anthropic` | 공식 SDK |
| 문서 파싱 | `pdfminer.six`, `python-docx`, `markdown-it-py` | |
| 산출물 | `python-pptx`, `openpyxl` | PPTX/XLSX 표준 |
| 저장 | OS Keychain (BYOK) / SQLite (옵션) | 키 보호 |
| 배포 | Electron 또는 Docker Compose | 데스크톱/사내 서버 양립 |

---

## 7. 데이터 모델 (요약)

```yaml
Project:
  id: uuid
  company_name: str
  project_name: str           # 예: "에코드림(ecoDream)"
  goal: text
  scope: text
  schedule: text
  org: text
  staff: text
  cost_dev: text
  cost_ops: text
  license: text
  availability: text
  budget: str
  attachments: [File]
  ai_provider: enum[openai|gemini|anthropic]
  ai_model: str
  outputs: [Artifact]

Artifact:
  type: enum[pptx|xlsx]
  path: str
  generated_at: datetime
```

---

## 8. API 설계 (요약)

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/llm/test` | 연결 테스트 (provider, model, apiKey) |
| POST | `/api/files/analyze` | 첨부 파싱 + 요약 → 사업 정보 초안 반환 |
| POST | `/api/projects` | 사업 정보 저장 |
| POST | `/api/generate/pptx` | PPTX 생성 → 파일 다운로드 |
| POST | `/api/generate/wbs` | WBS XLSX 생성 → 파일 다운로드 |

---

## 9. UI/UX (이미지 매핑)

| 영역 | 컴포넌트 | 비고 |
|---|---|---|
| ① AI 서비스 선택 | `<ProviderCardGroup />` 3카드 + 키/모델 입력 | 다크 테마 |
| ② 데이터 분석 | `<UploadDropzone />` 2슬롯 + `[분석 시작]` | 드래그&드롭 |
| ③ 사업 정보 | `<ProjectForm />` 12필드 | F2 결과 자동 바인딩 |
| ④ 산출물 | `<OutputCheckbox />` + 2 액션 버튼 | 진행률 표시 |
| ⑤ 카테고리 | `<CategoryCardGrid />` | 클릭 시 본문 편집 모달 |

---

## 10. 비기능 요구사항

| 항목 | 목표 |
|---|---|
| 성능 | PPTX 생성 ≤ 15초 (요건 30개 기준) |
| 보안 | API 키 평문 저장 금지(AES-256 + OS 키체인), 모든 통신 HTTPS |
| 개인정보 | 업로드 문서는 세션 종료 시 즉시 삭제 |
| 가용성 | 단일 PC 1인 사용, 서버 모드 99% (사내) |
| 다국어 | 한국어 기본, 영어 옵션 |

---

## 11. 마일스톤 (제안)

| Phase | 기간(주) | 주요 산출 |
|---|---|---|
| M1. 셋업 | 1 | 레포 초기화, FE/BE 스캐폴드, 디자인 토큰 |
| M2. AI 라우터 | 1 | 3사 LLM 어댑터 + 연결 테스트 |
| M3. 문서 분석 | 1.5 | 업로드/파싱/요약 → 폼 자동 채움 |
| M4. PPTX 생성 | 2 | 표준 목차 템플릿, 슬라이드 7종 |
| M5. WBS 생성 | 1.5 | XLSX 작업 분해, 일정 계산 |
| M6. QA/패키징 | 1 | Electron/Docker 배포, 사용자 매뉴얼 |
| **합계** | **8주** | MVP 출시 |

---

## 12. 리스크 & 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| LLM 토큰/비용 폭증 | 비용 | 청크 분할 + 캐시(요약) |
| 환각(hallucination) | 품질 | 인용 마킹, 사용자 검토 단계 강제 |
| 보안 사고(키 유출) | 신뢰 | BYOK + 키 로컬 저장만, 서버 비저장 |
| PPTX 디자인 한계 | UX | 템플릿 5종 사전 제작, 사후 수정 가이드 제공 |

---

## 13. 향후 확장(Backlog)

- 견적서 자동 생성, 인력 투입 계획서(M/M) 산출
- 사내 LLM(온프레미스) 어댑터 추가
- 과거 제안서 코퍼스 기반 RAG
- 한글(.hwp) 산출물 직접 출력

---

## 부록 A. 이미지 → 기능 매핑 표

| 이미지 영역 | 라벨 | 매핑 기능 |
|---|---|---|
| ① | AI 서비스 선택 / API 키 / 모델 / 연결·상태 | F1 |
| ② | 사업공고(공고문) + 관련 산출물 + 분석 시작 | F2 |
| ③ | 회사명 ~ 추진 예산 12개 필드 | F3 |
| ④ | 사업제안서(PPTX) / WBS(Excel) 체크 + 생성 버튼 | F4 |
| ⑤ | 사업개요·일반사항·기술 요구사항 등 카테고리 카드 | F5 |
