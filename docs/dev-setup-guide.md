# Lon — 개발환경 구성 가이드 (Local Setup Guide)

- 문서 버전: v0.1
- 작성일: 2026-05-03
- 대상 OS: Windows 11 (64bit). macOS/Linux 절차는 부록 참고.
- 작업 루트: `D:\github\autoProposal`

---

## 1. 사전 요구사항

| 도구 | 버전 | 용도 | 확인 |
|---|---|---|---|
| **Node.js** | 24.x | FE (Next.js 14) | `node -v` |
| **pnpm** (권장) | 9.x | FE 패키지 매니저 | `pnpm -v` |
| **Python** | 3.12 | BE (FastAPI), 변환 스크립트 | `python --version` |
| **JDK** | 17 | (옵션) Flyway 등 도구 | `java -version` |
| **Maven** | 3.9.9 | (옵션) | `mvn -v` |
| **MariaDB** | 11.4 | 정형 DB | `mariadb --version` |
| **MongoDB** | 8.2.x | 비정형 DB | `mongod --version` |
| **Git** | 2.40+ | VCS | `git --version` |

> 본 PC에 위 항목은 모두 설치/검증되어 있음 (메모리 기준).

---

## 2. 디렉토리 구조 (권장)

```
D:\github\autoProposal\
├── .gitignore
├── README.md
├── docs\                 ← 산출물 6종 (기획서/설계서/...)
│
├── apps\
│   ├── web\              ← FE (Next.js 14 + Tailwind)
│   │   ├── package.json
│   │   ├── pnpm-lock.yaml
│   │   └── src\
│   │       ├── app\
│   │       └── components\
│   └── api\              ← BE (FastAPI)
│       ├── pyproject.toml
│       ├── app\
│       │   ├── main.py
│       │   ├── core\          (config, security, db)
│       │   ├── routers\       (llm, files, projects, generate)
│       │   ├── services\      (llm clients, parser, pptx, xlsx)
│       │   └── models\        (sqlalchemy, mongo schemas)
│       └── tests\
│
├── db\
│   ├── mariadb\
│   │   └── migration\         ← Flyway V1__init.sql, V2__... 
│   └── mongo\
│       └── migrations\        ← migrate-mongo
│
├── scripts\
│   ├── dev.ps1                ← 전체 실행
│   ├── seed.ps1               ← 초기 데이터
│   └── reset.ps1              ← DB 리셋
│
└── workspace\                 ← 사용자 첨부/산출물 (gitignore)
    ├── attachments\
    └── outputs\
```

> 현 시점 `D:\github\autoProposal` 는 git 저장소 내부 파일이 루트에 노출된 비정상 상태입니다.
> 위 구조로 새로 init 권장 (부록 D 참고).

---

## 3. 데이터베이스 셋업

### 3.1 MariaDB 11.4

#### 3.1.1 사용자/DB 생성
```sql
-- 관리자 콘솔
CREATE DATABASE lon
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER 'lon_app'@'localhost' IDENTIFIED BY 'CHANGE_ME_LON_2026';
GRANT ALL PRIVILEGES ON lon.* TO 'lon_app'@'localhost';
FLUSH PRIVILEGES;
```

#### 3.1.2 접속 확인
```powershell
mariadb -u lon_app -p -h 127.0.0.1 -P 3306 lon
```

#### 3.1.3 초기 스키마 (Flyway)
- `db/mariadb/migration/V1__init.sql` 에 `db-design.md` 2.5절 DDL 적재
- 실행:
```powershell
flyway -url="jdbc:mariadb://localhost:3306/lon" `
       -user=lon_app -password=CHANGE_ME_LON_2026 `
       -locations=filesystem:db/mariadb/migration migrate
```

### 3.2 MongoDB 8.2

#### 3.2.1 서비스/접속
```powershell
Get-Service MongoDB           # 실행 중 확인 (PersonalFinance에서 설치 검증됨)
mongosh "mongodb://localhost:27017"
```

#### 3.2.2 사용자/DB 생성
```javascript
use lon
db.createUser({
  user: "lon_app",
  pwd: "CHANGE_ME_LON_2026",
  roles: [{ role: "readWrite", db: "lon" }]
})
```

#### 3.2.3 마이그레이션 (migrate-mongo)
- `db/mongo/migrate-mongo-config.js` 작성, `db/mongo/migrations/` 에 초기화 스크립트
- 실행:
```powershell
cd db\mongo
npx migrate-mongo up
```

---

## 4. 백엔드 (FastAPI) 셋업

### 4.1 가상환경 / 의존성
```powershell
cd D:\github\autoProposal\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
# 또는
pip install fastapi uvicorn[standard] pydantic-settings sqlalchemy `
            mariadb pymysql pymongo `
            python-multipart pdfminer.six python-docx openpyxl python-pptx `
            openai google-genai anthropic `
            keyring cryptography apscheduler
```

### 4.2 환경 변수 (`apps/api/.env`)
```dotenv
APP_ENV=local
APP_PORT=8080
APP_BASE_URL=http://localhost:8080

# MariaDB
MARIADB_URL=mysql+pymysql://lon_app:CHANGE_ME_LON_2026@127.0.0.1:3306/lon?charset=utf8mb4

# MongoDB
MONGO_URL=mongodb://lon_app:CHANGE_ME_LON_2026@127.0.0.1:27017/lon?authSource=lon

# 보안
JWT_SECRET=replace_with_long_random
AES_MASTER_KEY=replace_base64_32bytes

# 파일 시스템
WORKSPACE_DIR=D:\github\autoProposal\workspace

# LLM (BYOK는 사용자가 화면에서 입력. 아래는 개발용 서버 키)
OPENAI_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
```

### 4.3 실행
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
- 헬스체크: `http://localhost:8080/healthz`
- OpenAPI: `http://localhost:8080/docs`

### 4.4 테스트
```powershell
pytest -q
```

---

## 5. 프론트엔드 (Next.js 14) 셋업

### 5.1 설치
```powershell
cd D:\github\autoProposal\apps\web
pnpm install
```

### 5.2 환경 변수 (`apps/web/.env.local`)
```dotenv
NEXT_PUBLIC_API_BASE=http://localhost:8080
NEXT_PUBLIC_APP_NAME=Lon
NEXT_PUBLIC_DEFAULT_PROVIDER=GEMINI
```

### 5.3 실행
```powershell
pnpm dev
```
- 화면: `http://localhost:5173` (Vite 사용 시) 또는 `http://localhost:3000` (Next dev 기본)
- 본 프로젝트는 메모리상 검증된 5173 포트 사용 권장 (Vite + React) 또는 Next.js 3000 중 택 1

### 5.4 빌드
```powershell
pnpm build
pnpm start
```

---

## 6. 통합 실행 스크립트 (PowerShell)

`scripts/dev.ps1`:
```powershell
# 1) DB 가용성 확인
$ok = $true
try { mariadb -u lon_app -p"CHANGE_ME_LON_2026" -h 127.0.0.1 -e "SELECT 1" lon | Out-Null } catch { $ok = $false; Write-Host "MariaDB 연결 실패" }
try { mongosh "mongodb://lon_app:CHANGE_ME_LON_2026@127.0.0.1:27017/lon?authSource=lon" --quiet --eval "db.runCommand({ping:1})" | Out-Null } catch { $ok = $false; Write-Host "Mongo 연결 실패" }
if (-not $ok) { exit 1 }

# 2) BE
Start-Process powershell -ArgumentList @(
  "-NoExit","-Command",
  "cd D:\github\autoProposal\apps\api; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8080"
)

# 3) FE
Start-Process powershell -ArgumentList @(
  "-NoExit","-Command",
  "cd D:\github\autoProposal\apps\web; pnpm dev"
)
```

---

## 7. 시드 / 리셋

### 7.1 표준 목차 시드 (`scripts/seed.ps1`)
```powershell
mariadb -u lon_app -p"CHANGE_ME_LON_2026" lon -e "
INSERT IGNORE INTO proposal_category(code, name_ko, sort_order, is_active) VALUES
('OVERVIEW','사업 개요',10,1),
('GENERAL','일반 사항',20,1),
('TECH_REQ','기술 요구사항',30,1),
('PM_REQ','사업관리 요구사항',40,1),
('SECURITY','보안 요구사항',50,1),
('CONSTRAINT','제약 조건',60,1),
('ETC','기타',90,1);
"
```

### 7.2 전체 리셋 (`scripts/reset.ps1`)
```powershell
mariadb -u root -p -e "DROP DATABASE IF EXISTS lon; CREATE DATABASE lon DEFAULT CHARACTER SET utf8mb4;"
mongosh --quiet --eval "use lon; db.dropDatabase();"
flyway ... migrate
npx migrate-mongo up
.\seed.ps1
```

---

## 8. 트러블슈팅

| 증상 | 원인/해결 |
|---|---|
| `mariadb` 명령 미인식 | `Path` 환경변수에 MariaDB `bin` 추가 |
| Mongo 연결 ECONNREFUSED | `Get-Service MongoDB` 시작, 27017 방화벽 |
| `pip install mariadb` 실패 | MariaDB Connector/C 사전 설치 |
| Korean 깨짐 (콘솔) | PowerShell `chcp 65001`, 폰트 NanumGothic Coding |
| 5173 포트 충돌 | Vite `--port 5174` 또는 Next 3000 사용 |
| OpenAI/Gemini SSL 오류 | 사내 프록시면 `HTTPS_PROXY` 설정 |
| Maven JDK 21 강제 (메모리 기록) | `JAVA_HOME=JDK17` 명시, `mvn -v`로 확인 |

---

## 9. CI/CD (옵션)

| 단계 | 도구 | 비고 |
|---|---|---|
| Lint | ESLint, ruff | PR 게이트 |
| Test | vitest, pytest | 커버리지 80% |
| Build | pnpm build, hatch | 도커 이미지 |
| Migrate | Flyway, migrate-mongo | 배포 직전 |
| Deploy | Docker Compose / Electron Installer | 단일 노드 |

---

## 부록 A. macOS / Linux 차이점
- 키체인: macOS Keychain / Linux Secret Service (`keyring` 백엔드 자동 선택)
- 서비스: `brew services start mariadb`, `brew services start mongodb-community@8.2`
- 경로 구분자 `/`

## 부록 B. .gitignore 권장
```
.venv/
node_modules/
dist/
.next/
.env
.env.*
workspace/
*.log
*.docx
*.pptx
*.xlsx
!docs/**/*.docx
```

## 부록 C. 점검 체크리스트
- [ ] MariaDB `lon` DB / `lon_app` 계정 생성
- [ ] Mongo `lon` DB / `lon_app` 계정 생성
- [ ] Flyway, migrate-mongo 1회 성공
- [ ] BE `/healthz` 200, `/docs` 정상
- [ ] FE 메인 화면 진입, AI 키 등록 → 연결 테스트 OK
- [ ] PPTX 1건, XLSX 1건 생성/다운로드 확인

## 부록 D. 저장소 정리 (현재 비정상 상태 복구)
현재 `D:\github\autoProposal\` 루트에 `.git` 내부 파일들(HEAD, config, refs/...)이 노출돼 있습니다.
이 상태에서는 `git status` 가 동작하지 않습니다. 정상화 절차:

```powershell
# 1) 현재 노출된 git 메타 백업
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory "D:\github\autoProposal\.git_broken_$ts" | Out-Null
Move-Item D:\github\autoProposal\HEAD,D:\github\autoProposal\config,D:\github\autoProposal\description,`
          D:\github\autoProposal\hooks,D:\github\autoProposal\info,D:\github\autoProposal\objects,D:\github\autoProposal\refs `
          "D:\github\autoProposal\.git_broken_$ts\"

# 2) 새로 init + remote 연결
cd D:\github\autoProposal
git init
git remote add origin https://github.com/zeldahub/autoProposal.git
git fetch origin
git checkout -b main origin/main   # 원격 main이 비어 있으면 생략하고 로컬 main 생성

# 3) 산출물 커밋
git add docs/
git commit -m "docs: 초기 산출물 6종 작성 (기획/화면/DB/연계/메뉴/환경)"
```

> 위 절차 실행 전 반드시 백업 폴더(`.git_broken_*`)를 별도 위치에 보관하세요.
