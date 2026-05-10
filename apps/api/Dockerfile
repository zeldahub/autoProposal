# syntax=docker/dockerfile:1.6
# Lon API 컨테이너 — FastAPI + uvicorn (Python 3.12)
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 시스템 패키지 — pymysql 빌드, pdfminer 의 일부 옵셔널 의존성 등 (없어도 동작하지만 경고 방지)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 설치 (캐시 효율)
COPY pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip \
    && pip install . \
    && pip install "bcrypt>=4.1"

COPY app /app/app
COPY tests /app/tests

# 컨테이너 안에서는 workspace 를 마운트 받음
ENV WORKSPACE_DIR=/data/workspace \
    APP_PORT=8089

RUN mkdir -p /data/workspace/attachments /data/workspace/outputs

EXPOSE 8089
HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=15s \
    CMD curl -f http://127.0.0.1:8089/healthz || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8089"]
