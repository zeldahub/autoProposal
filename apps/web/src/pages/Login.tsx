import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useAuth } from "../auth/context";

export default function Login() {
  const { login, register, loading } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const redirect = params.get("redirect") || "/generator";

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("smoke@example.com");
  const [password, setPassword] = useState("secret123");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, displayName || undefined);
      }
      nav(redirect, { replace: true });
    } catch (e: any) {
      const msg = e?.response?.data?.error?.message
        || e?.response?.data?.detail
        || e?.message
        || "오류가 발생했습니다";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-bg">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 text-3xl font-bold text-primary">
            <Sparkles size={28} /> Lon
          </div>
          <div className="text-xs text-white/40 mt-1">AI 사업제안서 자동 생성기</div>
        </div>

        <div className="card">
          <div className="flex gap-1 mb-5 p-1 bg-bg rounded-md">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`flex-1 py-2 text-sm rounded ${mode === "login" ? "bg-primary text-white" : "text-white/60"}`}
            >로그인</button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={`flex-1 py-2 text-sm rounded ${mode === "register" ? "bg-primary text-white" : "text-white/60"}`}
            >회원가입</button>
          </div>

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="label">이메일</label>
              <input className="input" type="email" autoComplete="email" required
                value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">비밀번호</label>
              <input className="input" type="password" autoComplete="current-password" required minLength={6}
                value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            {mode === "register" && (
              <div>
                <label className="label">표시 이름 (선택)</label>
                <input className="input" type="text"
                  value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
              </div>
            )}

            {error && <div className="text-xs text-danger bg-danger/10 px-3 py-2 rounded border border-danger/30">{error}</div>}

            <button className="btn-primary w-full" disabled={loading}>
              {loading ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}
            </button>
          </form>
        </div>

        <div className="text-[11px] text-white/30 text-center mt-4">
          개발용 기본 계정: smoke@example.com / secret123
        </div>
      </div>
    </div>
  );
}
