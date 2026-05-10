# Lon — Docker Compose 가이드

## 빠른 시작

```bash
cp .env.example .env       # 비밀번호/시크릿 수정 권장
docker compose up --build -d
docker compose logs -f api
```

서비스:
- Web (nginx + Vite 빌드): http://localhost:8080
- API (uvicorn 8089): http://localhost:8089/healthz
- MariaDB: localhost:3306 (lon_app / lon)
- MongoDB: localhost:27017 (lon_app / lon)

`web` 컨테이너의 nginx 가 `/api/*` 요청을 `api` 컨테이너로 프록시하므로,
브라우저에서는 http://localhost:8080 만 접근하면 됩니다.

## 데이터베이스 초기화

- MariaDB: `docker-entrypoint-initdb.d` 가 처음 기동할 때
  `db/mariadb/migration/V1__init.sql ~ V5__collaboration.sql` 을 자동 실행합니다.
- MongoDB: `infra/mongo-init.js` 가 첫 기동 시
  `lon_app` 사용자 생성 + 컬렉션/인덱스 셋업.

기존 볼륨이 남아 있다면 init 스크립트는 다시 실행되지 않습니다 (Mongo/MariaDB 동작).
새로 시작하려면:

```bash
docker compose down -v   # 볼륨까지 삭제 (DB 데이터 손실)
docker compose up --build -d
```

## 로그 / 셸

```bash
docker compose logs -f api web mariadb mongo
docker compose exec api  bash
docker compose exec mariadb mariadb -ulon_app -p lon
docker compose exec mongo mongosh -u lon_app -p --authenticationDatabase lon lon
```

## 마이그레이션 추가 적용

V5 이후 새 SQL 을 만들면, 기존 컨테이너에는 자동 적용되지 않습니다 (initdb 는 1회).
운영 흐름:

```bash
# 새 마이그레이션 SQL 을 한 번 실행
docker compose exec mariadb sh -c \
  'mariadb -ulon_app -pCHANGE_ME_LON_2026 lon < /docker-entrypoint-initdb.d/V6__xyz.sql'
```

## 헬스체크

```bash
curl http://localhost:8080/healthz   # web (nginx)
curl http://localhost:8089/healthz   # api
```

## 트러블슈팅

- API 가 mariadb 헬스체크 실패로 못 떠요 → `docker compose logs mariadb` 확인.
  볼륨에 이전 비밀번호가 남아있다면 `docker compose down -v`.
- 첨부/산출물이 사라졌어요 → `workspace-data` 볼륨에 저장됩니다.
  볼륨을 백업하려면 `docker run --rm -v lon_workspace-data:/d -v $PWD:/b alpine \
    tar czf /b/workspace.tgz -C /d .`
- Windows 에서 Korean 파일명이 깨져요 → API 의 Content-Disposition 은 RFC5987
  (filename\*) 을 사용합니다. 모던 브라우저는 자동 처리.
