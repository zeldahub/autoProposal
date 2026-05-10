# Lon — FE (Vite + React + TypeScript + Tailwind)

## 실행

```powershell
cd D:\github\autoProposal\apps\web
pnpm install
copy .env.example .env.local
pnpm dev
```

- 화면: http://localhost:5173
- API 프록시: `/api` → `http://localhost:8080`

## 구조
```
src/
├── main.tsx
├── App.tsx
├── index.css
├── api/client.ts
├── components/Layout.tsx
└── pages/
    ├── Dashboard.tsx
    └── Generator.tsx     이미지 메인 화면 구현
```
