import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Users, FileSearch, ListTree, Activity } from "lucide-react";
import clsx from "clsx";

const ADMIN_NAV = [
  { to: "/admin", end: true, label: "대시보드", icon: LayoutDashboard },
  { to: "/admin/users", label: "사용자", icon: Users },
  { to: "/admin/audit", label: "감사 로그", icon: FileSearch },
  { to: "/admin/category", label: "표준 목차", icon: ListTree },
  { to: "/admin/jobs", label: "잡 모니터", icon: Activity },
];

export default function AdminLayout() {
  return (
    <div className="flex gap-6">
      <nav className="w-44 shrink-0 space-y-1">
        <div className="text-xs font-semibold text-white/40 px-3 mb-2">관리</div>
        {ADMIN_NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2 px-3 py-2 rounded-md text-sm",
                isActive ? "bg-primary/15 text-primary" : "text-white/70 hover:bg-white/5"
              )
            }
          >
            <Icon size={14} /> {label}
          </NavLink>
        ))}
      </nav>
      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
