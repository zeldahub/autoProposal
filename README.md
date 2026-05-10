# Lon — AI 사업제안서 자동 생성기

공고문/관련 산출물(MD/PDF/DOCX)을 업로드하고 사업 정보를 입력하면, 생성형 AI(ChatGPT / Gemini / Claude)를 활용해 **사업제안서 PPTX** 와 **WBS XLSX** 를 자동 생성합니다.

---

## 빠른 시작

### 0) 사전 요구사항 (본 PC 검증 완료)
| 도구 | 버전 |
|---|---|
| Node.js + pnpm | 24 / 9 |
| Python | 3.12 |
| MariaDB | 11.4 |
| MongoDB | 8.2 |

### 1) 1회 환경 점검
```powershell
.\scripts\check.ps1
```

### 2) 의존성 설치
```powershell
.\scripts\install.ps1
```

### 3) DB 초기화
```powershell
# 1차: 사용자/스키마 생성
.\scripts\reset.ps1
# 2차: 시드 데이터
.\scripts\seed.ps1
```

### 4) 실행
```powershell
.\scripts\dev.ps1
# BE: http://localhost:8080/docs
# FE: http://localhost:5173
```

---

## 구조

```
autoProposal/
├── apps/
│   ├── api/             FastAPI (Python 3.12)
│   └── web/             Vite + React + TS + Tailwind
├── db/
│   ├── mariadb/         초기 SQL (V1/V2)
│   └── mongo/           초기 JS
├── docs/                산출물 (md/docx/pptx/xlsx)
├── scripts/             dev/install/reset/seed/check
└── workspace/           첨부/산출물 (gitignore)
```

---

## 산출물 (`docs/`)
- 서비스 기획서 / 화면 설계서 / DB 설계서 / 연계 정의서 / 메뉴 구성도 / 개발환경 가이드
- `screen-design.pptx`, `db-design.xlsx`, `interface-spec.xlsx`, `api-architecture.xlsx`

자세한 설계 내용은 [docs/](docs/) 참고.
