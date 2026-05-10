# syntax=docker/dockerfile:1.6
# Lon Web — Vite 빌드 후 nginx 로 정적 서빙 + /api 프록시
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
ENV VITE_API_BASE=/api
RUN npm run build

# ── Runtime: nginx ──
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=5s \
    CMD wget -q -O - http://127.0.0.1/healthz || exit 1
