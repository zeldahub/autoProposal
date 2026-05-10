import { useEffect, useState } from "react";
import { Search, Loader2, RefreshCw } from "lucide-react";
import { adminListAudit, type AuditEntry } from "../../api/client";
import { formatDate, shortUuid } from "../../lib/format";

const ACTION_CHIPS: Record<string, string> = {
  "PROJECT.CREATE": "bg-accent/15 text-accent",
  "PROJECT.UPDATE": "bg-primary/15 text-primary",
  "PROJECT.DELETE": "bg-danger/15 text-danger",
  "USER.ROLE_CHANGE": "bg-primary/15 text-primary",
  "USER.DELETE": "bg-danger/15 text-danger",
  "AISET.CREATE": "bg-accent/15 text-accent",
  "AISET.DELETE": "bg-danger/15 text-danger",
  "CATEGORY.CREATE": "bg-accent/15 text-accent",
  "CATEGORY.DELETE": "bg-danger/15 text-danger",
};

export default function AdminAudit() {
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [action, setAction] = useState("");
  const [loading, setLoading] = useState(false);
  const SIZE = 50;

  const reload = async (p = page, a = action) => {
    setLoading(true);
    try {
      const data = await adminListAudit({ page: p, size: SIZE, action: a || undefined });
      setItems(data.items); setTotal(data.total); setPage(p);
    } finally { setLoading(false); }
  };

  useEffect(() => { reload(0, ""); }, []);

  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">감사 로그</h1>
        <span className="text-sm text-white/40">총 {total}건</span>
        <button className="btn-ghost ml-auto" onClick={() => reload(page, action)}>
          <RefreshCw size={14} className="mr-1" />새로고침
        </button>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); reload(0, action); }} className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input className="input pl-9" placeholder="액션 LIKE 검색 (예: PROJECT, AISET, CATEGORY)"
                 value={action} onChange={(e) => setAction(e.target.value)} />
        </div>
        <button className="btn-ghost">검색</button>
      </form>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-white/50 border-b border-white/5">
              <th className="px-4 py-3 w-16">#</th>
              <th className="px-4 py-3 w-12">UID</th>
              <th className="px-4 py-3 w-44">액션</th>
              <th className="px-4 py-3 w-36">대상</th>
              <th className="px-4 py-3">메타</th>
              <th className="px-4 py-3 w-44">시각</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-white/40">
                <Loader2 className="inline animate-spin mr-2" size={14} /> 로딩 중...
              </td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-white/40">감사 로그 없음</td></tr>
            )}
            {!loading && items.map((r) => (
              <tr key={r.id} className="border-b border-white/5 hover:bg-white/5 align-top">
                <td className="px-4 py-3 text-white/40 text-xs">{r.id}</td>
                <td className="px-4 py-3 text-white/40 text-xs">{r.userId ?? "-"}</td>
                <td className="px-4 py-3">
                  <span className={`text-[11px] px-2 py-0.5 rounded ${ACTION_CHIPS[r.action] || "bg-white/5 text-white/70"}`}>
                    {r.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-white/60">
                  {r.targetType ? <div>{r.targetType}</div> : "-"}
                  {r.targetUuid && <div className="font-mono text-white/40">{shortUuid(r.targetUuid)}</div>}
                </td>
                <td className="px-4 py-3 text-xs text-white/60 font-mono">
                  {r.meta ? JSON.stringify(r.meta) : "-"}
                </td>
                <td className="px-4 py-3 text-xs text-white/50">{formatDate(r.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 text-sm">
          <button className="btn-ghost" disabled={page === 0} onClick={() => reload(page - 1, action)}>이전</button>
          <span className="px-3 py-2 text-white/50">{page + 1} / {totalPages}</span>
          <button className="btn-ghost" disabled={page + 1 >= totalPages} onClick={() => reload(page + 1, action)}>다음</button>
        </div>
      )}
    </div>
  );
}
