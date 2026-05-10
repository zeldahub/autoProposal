import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API 백엔드 주소: env 로 덮어쓸 수 있고 기본값은 로컬 uvicorn 8089
const API_TARGET = process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8089";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
        // 백엔드가 잠깐 끊겨도 브라우저에는 502 로 응답 (500 대신)
        configure(proxy) {
          proxy.on("error", (err, _req, res) => {
            try {
              if (res && !res.headersSent) {
                res.writeHead(502, { "Content-Type": "application/json" });
              }
              res?.end(JSON.stringify({
                error: { code: "LON-PROXY-502", message: `API 서버 연결 실패: ${err.message}` },
              }));
            } catch {
              // ignore
            }
          });
        },
      },
    },
  },
});
