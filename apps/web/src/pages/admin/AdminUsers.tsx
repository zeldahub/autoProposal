import { useEffect, useState } from "react";
import { Search, Trash2, Loader2, Shield, ShieldOff } from "lucide-react";
import clsx from "clsx";
import { adminListUsers, adminUpdateUser, adminDeleteUser, type AdminUser } from "../../api/client";
import { formatDate } from "../../lib/format";
import { useAuth } from "../../auth/context";
import { useConfirm } from "../../ui/confirm/ConfirmProvider";
import { useToast } from "../../ui/toast/ToastProvider";

export default function AdminUsers() {
  const { user: me } = useAuth();
  const [items, setItems] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const confirm = useConfirm();
  const toast = useToast();
  const SIZE = 20;

  const reload = async (p = page, query = q) => {
    setLoading(true);
    try {
      const data = await adminListUsers({ page: p, size: SIZE, q: query || undefined });
      setItems(data.items); setTotal(data.total); setPage(p);
    } finally { setLoading(false); }
  };

  useEffect(() => { reload(0, ""); }, []);

  const toggleRole = async (u: AdminUser) => {
    const next = u.role === "ADMIN" ? "USER" : "ADMIN";
    const ok = await confirm({
      title: `${u.email}`,
      message: `권한을 ${u.role} → ${next} 로 변경합니다.`,
      confirmLabel: "변경",
      variant: next === "ADMIN" ? "warning" : "info",
    });
    if (!ok) return;
    setBusyId(u.id);
    try {
      await adminUpdateUser(u.id, next);
      toast.success(`${u.email} → ${next}`);
      await reload(page, q);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "변경 실패");
    } finally { setBusyId(null); }
  };

  const onDelete = async (u: AdminUser) => {
    const ok = await confirm({
      title: "사용자 삭제",
      message: `'${u.email}' 계정을 삭제하시겠습니까?`,
      description: "논리 삭제 — 데이터는 보존되지만 로그인 불가가 됩니다.",
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    setBusyId(u.id);
    try {
      await adminDeleteUser(u.id);
      toast.success("사용자가 삭제되었습니다.");
      await reload(page, q);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "삭제 실패");
    } finally { setBusyId(null); }
  };

  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">사용자 관리</h1>
        <span className="text-sm text-white/40">총 {total}명</span>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); reload(0, q); }} className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input className="input pl-9" placeholder="이메일 / 이름 검색" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <button className="btn-ghost">검색</button>
      </form>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-white/50 border-b border-white/5">
              <th className="px-4 py-3 w-12">#</th>
              <th className="px-4 py-3">이메일</th>
              <th className="px-4 py-3 w-32">표시 이름</th>
              <th className="px-4 py-3 w-24">권한</th>
              <th className="px-4 py-3 w-44">최근 로그인</th>
              <th className="px-4 py-3 w-44">가입</th>
              <th className="px-4 py-3 w-28"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-white/40">
                <Loader2 className="inline animate-spin mr-2" size={14} /> 로딩 중...
              </td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-white/40">사용자 없음</td></tr>
            )}
            {!loading && items.map((u) => {
              const isMe = me?.email === u.email;
              return (
                <tr key={u.id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="px-4 py-3 text-white/40 text-xs">{u.id}</td>
                  <td className="px-4 py-3">
                    {u.email}
                    {isMe && <span className="ml-2 text-[10px] text-accent">(나)</span>}
                  </td>
                  <td className="px-4 py-3 text-white/60">{u.displayName || "-"}</td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      "inline-flex items-center text-[11px] px-2 py-0.5 rounded",
                      u.role === "ADMIN" ? "bg-primary/15 text-primary" : "bg-white/5 text-white/60"
                    )}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-white/50">{formatDate(u.lastLoginAt)}</td>
                  <td className="px-4 py-3 text-xs text-white/50">{formatDate(u.createdAt)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="inline-flex p-1.5 hover:bg-white/10 rounded"
                      onClick={() => toggleRole(u)}
                      disabled={busyId === u.id || isMe}
                      title={u.role === "ADMIN" ? "USER로" : "ADMIN으로"}
                    >
                      {u.role === "ADMIN" ? <ShieldOff size={14} /> : <Shield size={14} />}
                    </button>
                    <button
                      className="inline-flex p-1.5 hover:bg-danger/20 hover:text-danger rounded ml-1"
                      onClick={() => onDelete(u)}
                      disabled={busyId === u.id || isMe}
                      title="삭제"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 text-sm">
          <button className="btn-ghost" disabled={page === 0} onClick={() => reload(page - 1, q)}>이전</button>
          <span className="px-3 py-2 text-white/50">{page + 1} / {totalPages}</span>
          <button className="btn-ghost" disabled={page + 1 >= totalPages} onClick={() => reload(page + 1, q)}>다음</button>
        </div>
      )}
    </div>
  );
}
