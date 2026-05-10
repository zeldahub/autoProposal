import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, RefreshCw, Trash2, RotateCcw, Loader2, AlertTriangle } from "lucide-react";
import {
  listTrashProjects, restoreProject, purgeProject,
  type TrashItem,
} from "../api/client";
import { formatDate, shortUuid } from "../lib/format";
import { useConfirm } from "../ui/confirm/ConfirmProvider";
import { useToast } from "../ui/toast/ToastProvider";

export default function ProjectsTrash() {
  const [items, setItems] = useState<TrashItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const confirm = useConfirm();
  const toast = useToast();
  const SIZE = 20;

  const reload = async (p = page) => {
    setLoading(true);
    try {
      const data = await listTrashProjects({ page: p, size: SIZE });
      setItems(data.items);
      setTotal(data.total);
      setPage(p);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(0); }, []);

  const handleRestore = async (it: TrashItem) => {
    const ok = await confirm({
      title: "사업 복구",
      message: `"${it.projectName}" 을 복구하시겠습니까?`,
      description: "복구 후 사업 목록에서 다시 사용할 수 있습니다.",
      confirmLabel: "복구",
    });
    if (!ok) return;
    setBusyId(it.uuid);
    try {
      await restoreProject(it.uuid);
      toast.success("사업이 복구되었습니다.");
      await reload(page);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "복구 실패");
    } finally {
      setBusyId(null);
    }
  };

  const handlePurge = async (it: TrashItem) => {
    const ok = await confirm({
      title: "영구 삭제",
      message: `"${it.projectName}" 을 영구 삭제하시겠습니까?`,
      description: `산출물 ${it.artifactCount}건과 첨부 파일이 모두 삭제되며, 이 작업은 되돌릴 수 없습니다.`,
      confirmLabel: "영구 삭제",
      variant: "danger",
    });
    if (!ok) return;
    setBusyId(it.uuid);
    try {
      const r = await purgeProject(it.uuid);
      toast.success(`영구 삭제 완료 (산출물 ${r.artifactCount}건, 첨부 ${r.attachmentCount}건)`);
      await reload(page);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "삭제 실패");
    } finally {
      setBusyId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/projects" className="btn-ghost">
          <ArrowLeft size={14} className="mr-1" /> 사업 목록
        </Link>
        <h1 className="text-2xl font-bold">휴지통</h1>
        <span className="text-sm text-white/40">총 {total}건</span>
        <button className="btn-ghost ml-auto" onClick={() => reload(page)}>
          <RefreshCw size={14} className="mr-1" /> 새로고침
        </button>
      </div>

      <div className="flex items-start gap-2 px-4 py-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 text-xs rounded-md">
        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
        <div>
          영구 삭제 시 사업의 모든 산출물 파일, 첨부 파일, 분석 결과, LLM 호출 로그가 함께 제거되며 되돌릴 수 없습니다.
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-white/50 border-b border-white/5">
              <th className="px-4 py-3 w-24">UUID</th>
              <th className="px-4 py-3">사업명</th>
              <th className="px-4 py-3 w-40">회사명</th>
              <th className="px-4 py-3 w-20">산출물</th>
              <th className="px-4 py-3 w-44">삭제일</th>
              <th className="px-4 py-3 w-44">생성일</th>
              <th className="px-4 py-3 w-32"></th>
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
                휴지통이 비어 있습니다.
              </td></tr>
            )}
            {!loading && items.map((p) => (
              <tr key={p.uuid} className="border-b border-white/5 hover:bg-white/5">
                <td className="px-4 py-3 font-mono text-xs text-white/40">{shortUuid(p.uuid)}</td>
                <td className="px-4 py-3 text-white/80">{p.projectName}</td>
                <td className="px-4 py-3 text-white/60">{p.companyName || "-"}</td>
                <td className="px-4 py-3 text-xs text-white/60">{p.artifactCount}건</td>
                <td className="px-4 py-3 text-xs text-white/60">{formatDate(p.deletedAt)}</td>
                <td className="px-4 py-3 text-xs text-white/40">{formatDate(p.createdAt)}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    className="inline-flex items-center px-2 py-1 text-xs text-primary hover:bg-primary/10 rounded"
                    onClick={() => handleRestore(p)}
                    disabled={busyId === p.uuid}
                    title="복구"
                  >
                    <RotateCcw size={12} className="mr-1" /> 복구
                  </button>
                  <button
                    className="inline-flex items-center px-2 py-1 text-xs text-danger hover:bg-danger/10 rounded ml-1"
                    onClick={() => handlePurge(p)}
                    disabled={busyId === p.uuid}
                    title="영구 삭제"
                  >
                    <Trash2 size={12} className="mr-1" /> 영구삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 text-sm">
          <button className="btn-ghost" disabled={page === 0} onClick={() => reload(page - 1)}>이전</button>
          <span className="px-3 py-2 text-white/50">{page + 1} / {totalPages}</span>
          <button className="btn-ghost" disabled={page + 1 >= totalPages} onClick={() => reload(page + 1)}>다음</button>
        </div>
      )}
    </div>
  );
}
