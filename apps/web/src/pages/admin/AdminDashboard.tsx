import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Users, Folder, Package, FileSearch, ListTree, Sparkles } from "lucide-react";
import { adminStats, type AdminStats } from "../../api/client";

const CARDS: { key: keyof AdminStats; label: string; to?: string; Icon: any }[] = [
  { key: "users", label: "사용자", to: "/admin/users", Icon: Users },
  { key: "projects", label: "사업", Icon: Folder },
  { key: "artifacts", label: "산출물", Icon: Package },
  { key: "llmCalls", label: "LLM 호출", Icon: Sparkles },
  { key: "categories", label: "카테고리", to: "/admin/category", Icon: ListTree },
  { key: "auditEntries", label: "감사 로그", to: "/admin/audit", Icon: FileSearch },
];

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);

  useEffect(() => { adminStats().then(setStats).catch(() => {}); }, []);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">관리자 대시보드</h1>
      <div className="grid grid-cols-3 gap-4">
        {CARDS.map(({ key, label, to, Icon }) => {
          const value = stats?.[key] ?? "-";
          const inner = (
            <div className="card flex items-center gap-4">
              <div className="bg-primary/10 text-primary p-3 rounded-md">
                <Icon size={20} />
              </div>
              <div>
                <div className="text-xs text-white/50">{label}</div>
                <div className="text-2xl font-bold mt-0.5">{value}</div>
              </div>
            </div>
          );
          return to ? (
            <Link key={key} to={to} className="block hover:opacity-90">{inner}</Link>
          ) : (
            <div key={key}>{inner}</div>
          );
        })}
      </div>
    </div>
  );
}
