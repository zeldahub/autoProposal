import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Plus, Trash2, FolderOpen, Loader2, Archive } from "lucide-react";
import { listProjects, deleteProject } from "../api/client";
import { formatDate, shortUuid } from "../lib/format";
import StatusBadge from "../components/StatusBadge";
import { useConfirm } from "../ui/confirm/ConfirmProvider";
import { useToast } from "../ui/toast/ToastProvider";

type Item = {
  id: number; uuid: string; projectName: string; companyName?: string;
  status: string; aiProvider?: string; aiModel?: string;
  updatedAt?: string;
};

export default function Projects() {
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const confirm = useConfirm();
  const toast = useToast();
  const SIZE = 20;

  const reload = async (p = page, query = q) => {
    setLoading(true);
    try {
      const data = await listProjects(p, SIZE, query || undefined);
      setItems(data.items);
      setTotal(data.total);
      setPage(p);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(0, ""); }, []);

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    reload(0, q);
  };

  const onDelete = async (uuid: string) => {
    const ok = await confirm({
      title: "사업 삭제",
      message: "이 사업을 휴지통으로 이동하시겠습니까?",
      description: "논리 삭제이며, 산출물 메타는 유지됩니다.",
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    setBusyId(uuid);
    try {
      await deleteProject(uuid);
      toast.success("사업이 삭제되었습니다.");
      await reload(page, q);
    } finally {
      setBusyId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">사업 관리</h1>
        <span className="text-sm text-white/40">총 {total}건</span>
        <Link to="/projects/trash" className="btn-ghost ml-auto" title="휴지통">
          <Archive size={14} className="mr-1" /> 휴지통
        </Link>
        <Link to="/generator" className="btn-primary">
          <Plus size={14} className="mr-1" /> 신규 생성
        </Link>
      </div>

      <form onSubmit={onSearch} className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            className="input pl-9"
            placeholder="사업명 / 회사명 검색"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <button className="btn-ghost">검색</button>
      </form>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-white/50 border-b border-white/5">
              <th className="px-4 py-3 w-24">UUID</th>
              <th className="px-4 py-3">사업명</th>
              <th className="px-4 py-3 w-40">회사명</th>
              <th className="px-4 py-3 w-24">상태</th>
              <th className="px-4 py-3 w-32">AI</th>
              <th className="px-4 py-3 w-44">수정일</th>
              <th className="px-4 py-3 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-white/40">
                <Loader2 className="inline animate-spin mr-2" size={14} /> 로딩 중...
              </td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-white/40">
                저장된 사업이 없습니다. <Link to="/generator" className="text-primary">새로 만들기 →</Link>
              </td></tr>
            )}
            {!loading && items.map((p) => (
              <tr key={p.uuid} className="border-b border-white/5 hover:bg-white/5">
                <td className="px-4 py-3 font-mono text-xs text-white/40">{shortUuid(p.uuid)}</td>
                <td className="px-4 py-3">
                  <Link to={`/projects/${p.uuid}`} className="text-white hover:text-primary">
                    {p.projectName}
                  </Link>
                </td>
                <td className="px-4 py-3 text-white/70">{p.companyName || "-"}</td>
                <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                <td className="px-4 py-3 text-xs text-white/50">
                  {p.aiProvider ? `${p.aiProvider}` : "-"}
                </td>
                <td className="px-4 py-3 text-xs text-white/50">{formatDate(p.updatedAt)}</td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/projects/${p.uuid}`} className="inline-flex p-1.5 hover:bg-white/10 rounded" title="열기">
                    <FolderOpen size={14} />
                  </Link>
                  <button
                    className="inline-flex p-1.5 hover:bg-danger/20 hover:text-danger rounded ml-1"
                    onClick={() => onDelete(p.uuid)}
                    disabled={busyId === p.uuid}
                    title="삭제"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
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
