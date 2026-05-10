import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";

export type User = { email: string; uuid: string; role?: string };

type AuthState = {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const TOKEN_KEY = "lon.token";
const USER_KEY = "lon.user";

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(false);

  // 토큰 변경 → axios 헤더 동기화 + storage
  // (동기 finishAuth 가 이미 axios.defaults 를 갱신하므로 여기서는 정리(logout) 케이스 위주)
  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    } else {
      localStorage.removeItem(TOKEN_KEY);
      delete api.defaults.headers.common["Authorization"];
    }
  }, [token]);

  useEffect(() => {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  }, [user]);

  // 로그인/등록 성공 시 호출 — axios 헤더와 localStorage 를 동기적으로 먼저 갱신해서
  // 직후의 nav() 로 마운트되는 자식 페이지 useEffect 가 토큰 없이 API 를 호출하는
  // race condition 을 방지한다 (자식 useEffect 가 부모 AuthProvider 의 useEffect 보다
  // 먼저 실행되므로 setState 만으로는 부족함).
  const finishAuth = (data: { accessToken: string; user: User }) => {
    try {
      localStorage.setItem(TOKEN_KEY, data.accessToken);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    } catch { /* storage 실패 무시 */ }
    api.defaults.headers.common["Authorization"] = `Bearer ${data.accessToken}`;
    setToken(data.accessToken);
    setUser(data.user);
  };

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      if (data.error) throw new Error(data.error.message);
      finishAuth(data.data);
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email: string, password: string, displayName?: string) => {
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", { email, password, displayName });
      if (data.error) throw new Error(data.error.message);
      finishAuth(data.data);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      const { data } = await api.get("/auth/me");
      const u = data.data.user;
      setUser({ uuid: u.uuid, email: u.email, role: u.role });
    } catch {
      // 401 인터셉터가 처리
    }
  }, [token]);

  // 시작 시 한 번 — role/displayName 최신화
  useEffect(() => {
    if (token && user && !user.role) refreshUser();
  }, [token, user, refreshUser]);

  const value = useMemo<AuthState>(
    () => ({ user, token, loading, login, register, logout, refreshUser }),
    [user, token, loading, login, register, logout, refreshUser]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
