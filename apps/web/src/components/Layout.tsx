import { useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Sparkles, Home, Folder, Settings, Package, LogOut, Shield } from "lucide-react";
import clsx from "clsx";
import { useAuth } from "../auth/context";
import NotificationBell from "./NotificationBell";
import LangToggle from "./LangToggle";
import { useT } from "../i18n";

export default function Layout() {
  const { user, logout, refreshUser } = useAuth();
  const nav = useNavigate();
  const t = useT();

  // 진입 시 role 최신화 (관리자 메뉴 노출용)
  useEffect(() => { refreshUser(); /* eslint-disable-next-line */ }, []);

  const handleLogout = () => {
    logout();
    nav("/login", { replace: true });
  };

  const NAV: { to: string; label: string; icon: typeof Home; role: "USER" | "ADMIN" }[] = [
    { to: "/", label: t("nav.dashboard"), icon: Home, role: "USER" },
    { to: "/generator", label: t("nav.generator"), icon: Sparkles, role: "USER" },
    { to: "/projects", label: t("nav.projects"), icon: Folder, role: "USER" },
    { to: "/artifacts", label: t("nav.artifacts"), icon: Package, role: "USER" },
    { to: "/settings", label: t("nav.settings"), icon: Settings, role: "USER" },
    { to: "/admin", label: t("nav.admin"), icon: Shield, role: "ADMIN" },
  ];

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 border-r border-white/5 bg-surface/40 flex flex-col">
        <div className="px-5 py-5">
          <div className="text-2xl font-bold text-primary">Lon</div>
          <div className="text-xs text-white/40">AI 사업제안서</div>
        </div>
        <nav className="px-2 space-y-1">
          {NAV.filter((n) => n.role !== "ADMIN" || user?.role === "ADMIN").map(({ to, label, icon: Icon, role }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2 px-3 py-2 rounded-md text-sm",
                  isActive ? "bg-primary/15 text-primary" : "text-white/70 hover:bg-white/5",
                  role === "ADMIN" && "border-t border-white/5 mt-2 pt-3"
                )
              }
            >
              <Icon size={16} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-3 py-3 border-t border-white/5">
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              clsx(
                "block px-2 py-2 rounded-md text-xs",
                isActive ? "bg-primary/15 text-primary" : "text-white/50 hover:bg-white/5"
              )
            }
            title="내 프로필"
          >
            <div className="font-medium text-white/80 truncate">{user?.email}</div>
            <div className="text-white/40">{user?.role || "USER"}</div>
          </NavLink>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-white/70 hover:bg-white/5"
          >
            <LogOut size={14} /> {t("nav.logout")}
          </button>
        </div>
      </aside>

      <main className="flex-1">
        <header className="h-14 border-b border-white/5 px-6 flex items-center justify-between bg-surface/30">
          <div className="text-sm text-white/60">AI 사업제안서 자동 생성기</div>
          <div className="flex items-center gap-3">
            <LangToggle />
            <NotificationBell />
            <div className="text-xs text-white/40">v0.1</div>
          </div>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
