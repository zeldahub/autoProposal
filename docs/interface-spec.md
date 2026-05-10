# Lon — 연계 정의서 (Interface Specification)

- 문서 버전: v0.1
- 작성일: 2026-05-03
- 관련: `service-plan.md`, `db-design.md`

---

## 1. 연계 개요

### 1.1 연계 대상 일람
| ID | 구분 | 시스템 | 방향 | 프로토콜 | 인증 | 동기/비동기 |
|---|---|---|---|---|---|---|
| IF-001 | 외부 | OpenAI ChatGPT API | OUT | HTTPS/REST | Bearer (API Key) | 동기 |
| IF-002 | 외부 | Google Gemini API | OUT | HTTPS/REST | API Key (`x-goog-api-key`) | 동기 |
| IF-003 | 외부 | Anthropic Claude API | OUT | HTTPS/REST | `x-api-key` Header | 동기 |
| IF-101 | 내부 | FE ↔ BE | IN/OUT | HTTPS/REST(JSON) | Cookie/Session JWT | 동기 |
| IF-201 | 시스템 | OS 키체인 (Windows Credential Manager) | IN/OUT | OS API | OS 사용자 | 동기 |
| IF-202 | 시스템 | 로컬 파일 시스템 | IN/OUT | FS | OS 권한 | 동기 |
| IF-301 | 데이터 | MariaDB 11.4 | IN/OUT | TCP/3306 | user/password | 동기 |
| IF-302 | 데이터 | MongoDB 8.2 | IN/OUT | TCP/27017 | SCRAM | 동기 |
| IF-401 | 출력 | PPTX/XLSX 산출물 | OUT | FS | - | 비동기 (잡) |

### 1.2 공통 정책
- 통신: TLS 1.2+, 외부 호출 타임아웃 60s, 재시도 3회 (지수 백오프)
- 데이터 포맷: JSON (UTF-8), 시간 ISO-8601 UTC
- 오류 코드: BE 자체 코드(`LON-XXXX`) + HTTP 상태 동시 반환
- 로깅: 모든 외부 호출은 `llm_call_log` + `llmSessions`에 기록

---

## 2. 외부 LLM 연계

### IF-001. OpenAI (ChatGPT)
| 항목 | 값 |
|---|---|
| Endpoint | `POST https://api.openai.com/v1/chat/completions` |
| 인증 | `Authorization: Bearer {API_KEY}` |
| Content-Type | `application/json` |
| 타임아웃 | 60s |
| 재시도 | 5xx/Rate-Limit → 3회 (1s, 2s, 4s) |
| 모델 예 | `gpt-4o`, `gpt-4o-mini` |

요청 예:
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "<카테고리별 system prompt>"},
    {"role": "user", "content": "<공고문 요약 + 사업정보>"}
  ],
  "temperature": 0.4,
  "max_tokens": 4096
}
```

응답 매핑:
| 응답 키 | 저장 위치 |
|---|---|
| `choices[0].message.content` | `llmSessions.response.text` |
| `usage.prompt_tokens` | `llm_call_log.input_tokens` |
| `usage.completion_tokens` | `llm_call_log.output_tokens` |

### IF-002. Google Gemini
| 항목 | 값 |
|---|---|
| Endpoint | `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` |
| 인증 | Header `x-goog-api-key: {API_KEY}` (또는 query `?key=`) |
| 모델 예 | `gemini-2.5-flash`, `gemini-2.5-pro` |

요청 예:
```json
{
  "contents": [{
    "parts": [{ "text": "<프롬프트>" }]
  }],
  "generationConfig": { "temperature": 0.4, "maxOutputTokens": 4096 }
}
```

### IF-003. Anthropic Claude
| 항목 | 값 |
|---|---|
| Endpoint | `POST https://api.anthropic.com/v1/messages` |
| 인증 | `x-api-key: {API_KEY}` + `anthropic-version: 2023-06-01` |
| 모델 예 | `claude-opus-4-7`, `claude-sonnet-4-6` |

요청 예:
```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 4096,
  "system": "<system prompt>",
  "messages": [{ "role": "user", "content": "<프롬프트>" }]
}
```

### 공통 오류 매핑
| 외부 코드 | 의미 | 내부 코드 | 사용자 메시지 |
|---|---|---|---|
| 401 | 인증 실패 | `LON-LLM-401` | API 키가 유효하지 않습니다 |
| 403 | 권한/지역 차단 | `LON-LLM-403` | 사용 권한이 없습니다 |
| 429 | Rate Limit | `LON-LLM-429` | 잠시 후 다시 시도해 주세요 |
| 5xx | 서버 오류 | `LON-LLM-5XX` | LLM 서비스 일시 장애 |
| Timeout | 타임아웃 | `LON-LLM-TO` | 응답 지연. 재시도 권장 |

---

## 3. 내부 API 연계 (IF-101 FE↔BE)

### 3.1 인증/세션
- 로컬 모드: 단일 사용자, 파일 기반 세션
- 멀티 모드: HttpOnly + Secure 쿠키 + JWT(15분) + Refresh(7일)

### 3.2 엔드포인트 명세

#### POST `/api/llm/test`
- 설명: API 키 유효성 검사 (1토큰 호출)
- 요청:
```json
{ "provider": "GEMINI", "model": "gemini-2.5-flash", "apiKey": "AIza..." }
```
- 응답 (200):
```json
{ "ok": true, "latencyMs": 320, "echo": "pong" }
```
- 오류: 400/401/429/500 + `{ "code": "LON-LLM-401", "message": "..." }`

#### POST `/api/files/analyze`
- 설명: 첨부 파싱 + 요약 + 사업정보 자동 채움
- 요청 (multipart/form-data):
  - `projectUuid` (form field, 선택; 없으면 임시 생성)
  - `notice` (file, ≤10MB, PDF/DOCX/TXT/MD)
  - `references[]` (file 0..N)
- 응답 (200):
```json
{
  "projectUuid": "...",
  "documents": [{ "id": "ObjectId", "slot": "NOTICE" }],
  "fields": {
    "projectName": "에코드림(ecoDream)",
    "goal": "...",
    "scope": "..."
  },
  "confidence": { "goal": 0.82 },
  "llmCallLogId": 12345
}
```

#### POST `/api/projects`
- 요청: `Project` 전체 필드(JSON)
- 응답: `{ "id": 1, "uuid": "..." }`

#### GET `/api/projects/:uuid`
- 응답: `Project` + 산출물/로그 요약

#### POST `/api/generate/pptx`
- 요청: `{ "projectUuid": "...", "categories": ["OVERVIEW","TECH_REQ", ...] }`
- 응답: `200 application/vnd.openxmlformats-officedocument.presentationml.presentation` (파일 다운로드)
- 부수효과: `proposalDrafts` + `artifact` row 생성

#### POST `/api/generate/wbs`
- 요청: `{ "projectUuid": "...", "phases": 5 }`
- 응답: `200 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

#### GET `/api/categories`
- 표준 목차 마스터 트리 반환

### 3.3 응답 공통 포맷
```json
{
  "data": { /* payload */ },
  "error": null,
  "traceId": "uuid-v4"
}
```
오류:
```json
{
  "data": null,
  "error": { "code": "LON-...", "message": "...", "details": {} },
  "traceId": "uuid-v4"
}
```

---

## 4. 시스템 연계

### IF-201. OS 키체인 (Windows)
- API: Windows Credential Manager (`Add-StoredCredential` / `Get-StoredCredential`)
- 라이브러리: `keyring` (Python)
- 키 네이밍: `Lon/{provider}/{userUuid}`
- 폴백: 키체인 사용 불가 시 MariaDB `ai_provider_setting`에 AES-256-GCM 암호문 저장

### IF-202. 로컬 파일 시스템
- 기본 작업 폴더: `%USERPROFILE%\Lon\workspace`
- 하위:
  - `attachments/{projectUuid}/`
  - `outputs/{projectUuid}/{type}/v{n}.{ext}`
- 파일명 sanitize: `[\\/:*?"<>|]` → `_`
- 디스크 여유 < 200MB 시 업로드 차단

---

## 5. 데이터 저장소 연계

### IF-301. MariaDB
| 항목 | 값 |
|---|---|
| Host/Port | `localhost:3306` |
| DB | `lon` |
| Driver | `mariadb-connector-python` 또는 `pymysql` |
| 풀 | size=10, recycle=1800s |
| 트랜잭션 | READ COMMITTED, FK 사용 |
| 초기화 | Flyway `V1__init.sql` |

### IF-302. MongoDB
| 항목 | 값 |
|---|---|
| URI | `mongodb://lon_app:<pwd>@localhost:27017/lon?authSource=lon` |
| Driver | `pymongo>=4.7` |
| 쓰기 보장 | `w=majority`, `j=true` |
| 마이그레이션 | `migrate-mongo` |

### Hybrid 트랜잭션 패턴
- 양 DB 동시 INSERT는 BE에서 의사-2PC 흐름:
  1) MariaDB `INSERT ... status='PENDING'`
  2) Mongo `insertOne(...)`
  3) MariaDB `UPDATE ... status='OK', mongo_*_id=...`
- 단계 실패 시 `status='ERROR'` 후 보상 잡(`mongo_repair`)이 정리

---

## 6. 비동기 / 잡 (IF-401)

| 잡 | 트리거 | 처리 |
|---|---|---|
| `pptx-generate` | `/api/generate/pptx` 큐 적재 | python-pptx로 작성 → `outputs/` 저장 → 완료 알림 |
| `xlsx-generate` | `/api/generate/wbs` | openpyxl |
| `mongo-repair` | 5분 주기 | `status='ERROR'` 행 보상 |
| `attachment-cleanup` | 1시간 주기 | 24h 경과 첨부 삭제 |

큐: 단일 노드 → `apscheduler` + sqlite job store. 멀티 노드 확장 시 Redis Stream로 교체.

---

## 7. 오류/재시도 정책

| 영역 | 정책 |
|---|---|
| 외부 LLM | 5xx/429만 재시도, 4xx는 즉시 반환 |
| DB | 일시 단절 → 5초 백오프 ×3 |
| 파일 IO | 권한 오류 즉시 반환, 디스크 풀 → 사용자 메시지 |
| 잡 실패 | 3회 재시도 후 DLQ 컬렉션 `failedJobs`로 이동 |

---

## 8. 보안 / 컴플라이언스

- 외부 LLM에 전달되는 본문에서 PII 마스킹 (휴대폰/주민/이메일 정규식 치환)
- LLM 응답 본문은 `llmSessions`에만 저장, FE에 마스킹 해제본 전송 없음
- 모든 외부 호출 도메인 화이트리스트:
  - `api.openai.com`
  - `generativelanguage.googleapis.com`
  - `api.anthropic.com`

---

## 9. 모니터링 지표

| 지표 | 임계 |
|---|---|
| LLM 평균 지연 | < 8s |
| LLM 오류율 | < 2% / 일 |
| DB 풀 사용률 | < 70% |
| 디스크 사용률 | < 80% |
| 잡 실패율 | < 1% |

수집: BE 로그 → `audit_log` + 콘솔. 추후 Prometheus/Grafana 연동.

---

## 부록 A. 환경별 엔드포인트
| 환경 | FE | BE | MariaDB | Mongo |
|---|---|---|---|---|
| 로컬 | http://localhost:5173 | http://localhost:8080 | localhost:3306 | localhost:27017 |
| 사내 | https://lon.intra | https://lon-api.intra | mariadb.intra:3306 | mongo.intra:27017 |
