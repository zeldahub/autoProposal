# Lon — DB 설계서 (Hybrid: MariaDB + MongoDB)

- 문서 버전: v0.1
- 작성일: 2026-05-03
- 대상 환경: Local (Windows) — MariaDB 11.4 / MongoDB 8.2
- 관련 문서: `service-plan.md`, `screen-design.md`

---

## 1. 설계 원칙

### 1.1 하이브리드 채택 사유
| 데이터 특성 | 저장소 | 사유 |
|---|---|---|
| 정형/관계형 (사용자, 사업 메타, 산출물 메타, 권한, 감사) | **MariaDB** | 트랜잭션, 외래키, 집계 쿼리 안정성 |
| 비정형/대용량 (LLM 입출력, 추출 텍스트, 슬라이드 JSON, WBS 트리, 임베딩) | **MongoDB** | 스키마 진화, 큰 문서, 배열/중첩 |

### 1.2 공통 규칙
- 문자 셋: MariaDB `utf8mb4 / utf8mb4_unicode_ci`, Mongo `UTF-8`
- 시간: 모두 **UTC** 저장, 표시 시점에 KST 변환
- PK: MariaDB `BIGINT AUTO_INCREMENT` + `uuid CHAR(36) UNIQUE`, Mongo `_id: ObjectId` + `uuid` 인덱스
- 논리 삭제: `deleted_at TIMESTAMP NULL` (MariaDB), `deletedAt: ISODate` (Mongo)
- 모든 테이블/컬렉션에 `created_at`, `updated_at` 보유
- 명명: MariaDB `snake_case`, Mongo `camelCase`

### 1.3 책임 분리(SoR)
- 사업의 "헤더(메타)"는 MariaDB가 SoR
- 사업의 "본문(LLM 산출 콘텐츠/원문/슬라이드 JSON)"은 MongoDB가 SoR
- MongoDB 문서는 MariaDB `project.uuid`를 외부키로 보유 (`projectUuid`)

---

## 2. MariaDB 설계

### 2.1 스키마/계정
```sql
CREATE DATABASE lon
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER 'lon_app'@'localhost' IDENTIFIED BY '<replace_me>';
GRANT ALL PRIVILEGES ON lon.* TO 'lon_app'@'localhost';
FLUSH PRIVILEGES;
```

### 2.2 ERD (논리)
```
user ──< project ──< artifact
              │  └─< llm_call_log
              └─< project_attachment
user ──< ai_provider_setting
user ──< audit_log
proposal_category (마스터)
```

### 2.3 테이블 정의

#### T-01. `user`
| 컬럼 | 타입 | NN | 기본 | 설명 |
|---|---|---|---|---|
| id | BIGINT AI | Y | - | PK |
| uuid | CHAR(36) | Y | UUID() | 외부 키 |
| email | VARCHAR(255) | Y | - | 로그인 ID, UNIQUE |
| password_hash | VARCHAR(255) | Y | - | bcrypt |
| display_name | VARCHAR(100) | N | - | 표시명 |
| role | ENUM('USER','ADMIN') | Y | 'USER' | 권한 |
| last_login_at | TIMESTAMP | N | - | |
| created_at | TIMESTAMP | Y | CURRENT_TIMESTAMP | |
| updated_at | TIMESTAMP | Y | CURRENT_TIMESTAMP ON UPDATE | |
| deleted_at | TIMESTAMP | N | NULL | 논리 삭제 |

#### T-02. `project`
| 컬럼 | 타입 | NN | 설명 |
|---|---|---|---|
| id | BIGINT AI | Y | PK |
| uuid | CHAR(36) | Y | UNIQUE |
| owner_id | BIGINT | Y | FK→user.id |
| company_name | VARCHAR(120) | N | 회사명 |
| project_name | VARCHAR(200) | Y | 사업명 |
| goal | TEXT | N | 사업 목표 |
| scope | TEXT | N | 사업 범위 |
| schedule | TEXT | N | 일정 |
| organization | TEXT | N | 수행 조직 |
| staff | TEXT | N | 수행 인력 |
| cost_dev | TEXT | N | 개발 비용 |
| cost_ops | TEXT | N | 운영 비용 |
| license_info | TEXT | N | 라이선스 |
| availability | TEXT | N | 가용성 |
| budget | VARCHAR(50) | N | 예산 |
| ai_provider | ENUM('OPENAI','GEMINI','ANTHROPIC') | N | |
| ai_model | VARCHAR(80) | N | |
| status | ENUM('DRAFT','READY','GENERATED','ARCHIVED') | Y | |
| created_at / updated_at / deleted_at | TIMESTAMP | | |

INDEX: `idx_project_owner(owner_id)`, `idx_project_name(project_name)`, `idx_project_status(status)`

#### T-03. `project_attachment`
| 컬럼 | 타입 | NN | 설명 |
|---|---|---|---|
| id | BIGINT AI | Y | PK |
| project_id | BIGINT | Y | FK |
| slot | ENUM('NOTICE','REFERENCE') | Y | 사업공고/관련산출물 |
| filename | VARCHAR(255) | Y | |
| mime_type | VARCHAR(100) | Y | |
| size_bytes | INT | Y | |
| sha256 | CHAR(64) | Y | 중복/무결성 |
| storage_path | VARCHAR(500) | Y | 로컬 경로 |
| mongo_doc_id | CHAR(24) | N | Mongo `documents._id` |
| created_at | TIMESTAMP | Y | |

INDEX: `idx_attach_project(project_id)`, `uq_attach_sha(project_id, sha256)`

#### T-04. `artifact` (산출물 메타)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT AI | PK |
| project_id | BIGINT NN | FK |
| type | ENUM('PPTX','XLSX') NN | |
| version | INT NN | 1부터 증가 |
| filename | VARCHAR(255) NN | |
| storage_path | VARCHAR(500) NN | |
| size_bytes | INT NN | |
| sha256 | CHAR(64) NN | |
| llm_call_log_id | BIGINT N | 어느 LLM 호출이 만들었는지 |
| mongo_draft_id | CHAR(24) N | Mongo `proposalDrafts._id` |
| created_at | TIMESTAMP | |

UNIQUE: `(project_id, type, version)`

#### T-05. `ai_provider_setting`
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT AI | PK |
| user_id | BIGINT NN | FK |
| provider | ENUM('OPENAI','GEMINI','ANTHROPIC') NN | |
| alias | VARCHAR(80) | 별칭 |
| api_key_cipher | VARBINARY(512) NN | AES-256-GCM 암호문 |
| key_iv | VARBINARY(16) NN | IV |
| key_tag | VARBINARY(16) NN | GCM tag |
| default_model | VARCHAR(80) | |
| temperature | DECIMAL(3,2) | 기본 0.4 |
| max_tokens | INT | |
| is_active | TINYINT(1) NN | 1 |
| last_verified_at | TIMESTAMP N | |
| created_at / updated_at | TIMESTAMP | |

UNIQUE: `(user_id, provider, alias)`

> **보안**: 키는 OS 키체인을 1차로 사용하고, 본 컬럼은 fallback. 평문 컬럼 금지.

#### T-06. `llm_call_log` (메타만; 본문은 Mongo)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT AI | PK |
| project_id | BIGINT NN | FK |
| provider | ENUM | |
| model | VARCHAR(80) | |
| purpose | ENUM('ANALYZE','GEN_PPTX','GEN_WBS','TEST') | |
| input_tokens | INT | |
| output_tokens | INT | |
| latency_ms | INT | |
| http_status | SMALLINT | |
| error_code | VARCHAR(50) N | |
| mongo_session_id | CHAR(24) N | Mongo `llmSessions._id` |
| created_at | TIMESTAMP | |

INDEX: `idx_llm_project(project_id)`, `idx_llm_purpose(purpose)`

#### T-07. `proposal_category` (표준 목차 마스터)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | INT AI | PK |
| code | VARCHAR(40) NN UNIQUE | 예: `OVERVIEW` |
| name_ko | VARCHAR(80) NN | 사업 개요 |
| parent_id | INT N | 자기참조 |
| sort_order | INT NN | |
| slide_template_key | VARCHAR(80) | python-pptx 템플릿 키 |
| system_prompt | TEXT | LLM 시스템 프롬프트 |
| is_active | TINYINT(1) NN | |
| created_at / updated_at | TIMESTAMP | |

#### T-08. `audit_log`
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT AI | PK |
| user_id | BIGINT N | |
| action | VARCHAR(80) NN | 예: `PROJECT.CREATE` |
| target_type | VARCHAR(40) | |
| target_uuid | CHAR(36) | |
| ip | VARCHAR(45) | |
| user_agent | VARCHAR(255) | |
| meta_json | JSON | 부가 정보 |
| created_at | TIMESTAMP | |

### 2.4 인덱스 / 성능 가이드
- 검색 컬럼: `project.project_name` 에 `FULLTEXT(ngram)` 인덱스
- 자주 쓰는 조인: `project.owner_id`, `artifact.project_id`
- 대용량 (Mongo로 위임): LLM 본문, 텍스트 청크는 MariaDB에 저장하지 않음

### 2.5 DDL 스니펫(예시)
```sql
CREATE TABLE project (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  uuid CHAR(36) NOT NULL UNIQUE,
  owner_id BIGINT NOT NULL,
  company_name VARCHAR(120),
  project_name VARCHAR(200) NOT NULL,
  goal TEXT, scope TEXT, schedule TEXT,
  organization TEXT, staff TEXT,
  cost_dev TEXT, cost_ops TEXT, license_info TEXT,
  availability TEXT, budget VARCHAR(50),
  ai_provider ENUM('OPENAI','GEMINI','ANTHROPIC'),
  ai_model VARCHAR(80),
  status ENUM('DRAFT','READY','GENERATED','ARCHIVED') NOT NULL DEFAULT 'DRAFT',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  CONSTRAINT fk_project_owner FOREIGN KEY (owner_id) REFERENCES user(id),
  INDEX idx_project_owner (owner_id),
  INDEX idx_project_status (status),
  FULLTEXT KEY ft_project_name (project_name) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 3. MongoDB 설계

### 3.1 데이터베이스/사용자
```js
use lon
db.createUser({
  user: "lon_app",
  pwd: "<replace_me>",
  roles: [{ role: "readWrite", db: "lon" }]
})
```

### 3.2 컬렉션 개요
| 컬렉션 | 용도 |
|---|---|
| `documents` | 업로드 원본의 추출 텍스트, 청크, (옵션) 임베딩 |
| `analysisResults` | 공고문 분석 → 사업정보 자동 채움 결과 |
| `llmSessions` | 모든 LLM 호출의 요청/응답 원문 |
| `proposalDrafts` | 슬라이드별 편집 가능한 초안 (PPTX 생성 전) |
| `wbsTasks` | WBS 작업 트리 (XLSX 생성 전) |
| `categoryPrompts` | 카테고리별 프롬프트 버전 이력 |

### 3.3 컬렉션 스키마

#### `documents`
```json
{
  "_id": "ObjectId",
  "projectUuid": "uuid-of-project",
  "attachmentId": 12345,            // MariaDB project_attachment.id
  "slot": "NOTICE",                 // NOTICE | REFERENCE
  "filename": "공고문.pdf",
  "mimeType": "application/pdf",
  "extractedText": "...",
  "chunks": [
    { "idx": 0, "text": "...", "tokens": 280, "embedding": [/* optional */] }
  ],
  "summary": "공고문 요약 1~2단락",
  "language": "ko",
  "createdAt": "ISODate"
}
```
- 인덱스: `{ projectUuid: 1 }`, `{ attachmentId: 1 }`
- (옵션) Atlas Vector Index: `chunks.embedding` (로컬 mongo면 IVF 미지원 → in-app 검색)

#### `analysisResults`
```json
{
  "_id": "ObjectId",
  "projectUuid": "...",
  "source": { "noticeDocId": "ObjectId", "referenceDocIds": ["ObjectId"] },
  "fields": {
    "projectName": "에코드림(ecoDream)",
    "goal": "...",
    "scope": "...",
    "schedule": "...",
    "license": "..."
  },
  "confidence": { "goal": 0.82, "scope": 0.74 },
  "model": "gemini-2.5-flash",
  "createdAt": "ISODate"
}
```

#### `llmSessions`
```json
{
  "_id": "ObjectId",
  "projectUuid": "...",
  "purpose": "GEN_PPTX",
  "provider": "GEMINI",
  "model": "gemini-2.5-flash",
  "request": {
    "system": "...",
    "messages": [/* 원문 */],
    "tools": [],
    "temperature": 0.4
  },
  "response": {
    "text": "...",
    "raw": {/* provider raw json */}
  },
  "usage": { "input": 5320, "output": 1820 },
  "latencyMs": 7800,
  "createdAt": "ISODate"
}
```
- 인덱스: `{ projectUuid: 1, createdAt: -1 }`, `{ purpose: 1 }`
- TTL(옵션): `expireAfterSeconds: 60*60*24*90` (90일 후 정리)

#### `proposalDrafts`
```json
{
  "_id": "ObjectId",
  "projectUuid": "...",
  "version": 1,
  "categories": [
    {
      "code": "OVERVIEW",
      "name": "사업 개요",
      "slides": [
        { "title": "사업 배경", "bullets": ["..."], "speakerNote": "..." }
      ]
    }
  ],
  "model": "gemini-2.5-flash",
  "createdAt": "ISODate"
}
```

#### `wbsTasks`
```json
{
  "_id": "ObjectId",
  "projectUuid": "...",
  "version": 1,
  "phases": [
    {
      "code": "P1",
      "name": "분석",
      "tasks": [
        { "code": "P1-T1", "name": "요건 정의", "owner": "PM", "durationDays": 5, "deliverables": ["요구사항 명세서"] }
      ]
    }
  ],
  "totalTasks": 80,
  "createdAt": "ISODate"
}
```

#### `categoryPrompts`
```json
{
  "_id": "ObjectId",
  "code": "OVERVIEW",
  "version": 3,
  "systemPrompt": "...",
  "userPromptTemplate": "...",
  "active": true,
  "createdAt": "ISODate"
}
```

### 3.4 인덱스 요약
| 컬렉션 | 인덱스 |
|---|---|
| documents | `{projectUuid:1}`, `{attachmentId:1}` |
| analysisResults | `{projectUuid:1}` |
| llmSessions | `{projectUuid:1, createdAt:-1}`, `{purpose:1}`, TTL 90d |
| proposalDrafts | `{projectUuid:1, version:-1}` |
| wbsTasks | `{projectUuid:1, version:-1}` |
| categoryPrompts | `{code:1, version:-1}`, partial `{active:true}` |

---

## 4. 데이터 흐름 (Hybrid)

```
[FE]→ POST /projects ─────────────► MariaDB.project (INSERT)
[FE]→ POST /files/analyze
   ├─ MariaDB.project_attachment (INSERT meta)
   ├─ Mongo.documents (INSERT 추출 텍스트)
   ├─ LLM 호출
   ├─ Mongo.llmSessions (INSERT 원문)
   ├─ Mongo.analysisResults (INSERT 정리 결과)
   └─ MariaDB.llm_call_log (INSERT 메타)
[FE]→ POST /generate/pptx
   ├─ Mongo.proposalDrafts (INSERT)
   ├─ python-pptx로 파일 생성
   └─ MariaDB.artifact (INSERT 메타) → 다운로드 응답
```

---

## 5. 일관성 / 트랜잭션 전략

- MariaDB ↔ MongoDB 간 분산 트랜잭션은 사용하지 않음
- 패턴: **Outbox + 보상 트랜잭션**
  - MariaDB INSERT 후, Mongo INSERT 실패 시 Mariadb row를 `status='ERROR'`로 업데이트
  - 백그라운드 잡(`mongo_repair`)이 5분 주기로 재시도/정리
- 식별자 동기화: `project.uuid`(MariaDB) ↔ `projectUuid`(Mongo) 단방향 참조

---

## 6. 보안

| 항목 | 정책 |
|---|---|
| API Key | OS 키체인 우선, fallback AES-256-GCM (`ai_provider_setting`) |
| DB 비밀번호 | `.env` + OS 사용자 권한 600 |
| PII | 첨부 원본은 세션 종료 시 또는 24h 후 자동 삭제 잡 |
| 감사 | 모든 변경 작업 `audit_log` 적재 |

---

## 7. 백업 / 운영

| 대상 | 주기 | 도구 | 보관 |
|---|---|---|---|
| MariaDB | 일 1회 | `mariadb-dump` (논리) + binlog | 14일 |
| MongoDB | 일 1회 | `mongodump` | 14일 |
| 첨부/산출물 | 주 1회 | `robocopy /MIR` | 30일 |

복구 RPO 24h, RTO 2h (단일 PC 기준).

---

## 8. 마이그레이션 / 버전 관리

- MariaDB: **Flyway** (`db/migration/V1__init.sql`, `V2__...sql`)
- MongoDB: **migrate-mongo** (`migrations/2026-05-03-init.js`)
- 두 DB 마이그레이션은 **동일 PR**에서 함께 관리, 버전 매핑은 `docs/db-version-map.md` (TBD)

---

## 부록 A. 카테고리 시드 데이터 예
| code | name_ko | sort |
|---|---|---|
| OVERVIEW | 사업 개요 | 10 |
| GENERAL | 일반 사항 | 20 |
| TECH_REQ | 기술 요구사항 | 30 |
| PM_REQ | 사업관리 요구사항 | 40 |
| SECURITY | 보안 요구사항 | 50 |
| CONSTRAINT | 제약 조건 | 60 |
| ETC | 기타 | 90 |
