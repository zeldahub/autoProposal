import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Trash2, FileText, FileSpreadsheet, Loader2, RefreshCw, Eye } from "lucide-react";
import clsx from "clsx";
import {
  listAllArtifacts, downloadArtifact, deleteArtifact,
  type ArtifactItem,
} from "../api/client";
import { downloadBlob, formatBytes, formatDate, shortUuid } from "../lib/format";
import { useConfirm } from "../ui/confirm/ConfirmProvider";
import { useToast } from "../ui/toast/ToastProvider";
import ArtifactPreviewDrawer from "../components/ArtifactPreviewDrawer";

type FilterType = "ALL" | "PPTX" | "XLSX";

export default function Artifacts() {
  const [items, setItems] = useState<ArtifactItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<FilterType>("ALL");
  const [loading, setLoading] = useState(false);
  const confirm = useConfirm();
  const toast = useToast();
  const [previewId, setPreviewId] = useState<number | null>(null);
  const SIZE = 30;

  const reload = async (p = page, f = filter) => {
    setLoading(true);
    try {
      const r = await listAllArtifacts({
        page: p, size: SIZE,
        type: f === "ALL" ? undefined : f,
      });
      setItems(r.items); setTotal(r.total); setPage(p);
    } finally { setLoading(false); }
  };

  useEffect(() => { reload(0, filter); /* eslint-disable-next-line */ }, [filter]);

  const handleDownload = async (a: ArtifactItem) => {
    const r = await downloadArtifact(a.id);
    downloadBlob(r.data, a.filename);
  };

  const handleDelete = async (a: ArtifactItem) => {
    const ok = await confirm({
      title: "산출물 삭제",
      message: `${a.type} v${a.version} 을 삭제하시겠습니까?`,
      description: `파일: ${a.filename}`,
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    await deleteArtifact(a.id);
    toast.success("산출물이 삭제되었습니다.");
    await reload(page, filter);
  };

  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">산출물 라이브러리</h1>
        <span className="text-sm text-white/40">총 {total}건</span>
        <button className="btn-ghost ml-auto" onClick={() => reload(page, filter)}>
          <RefreshCw size={14} className="mr-1" />새로고침
        </button>
      </div>

      <div className="flex gap-1 p-1 bg-surface rounded-md w-fit">
        {(["ALL", "PPTX", "XLSX"] as FilterType[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              "px-3 py-1.5 text-sm rounded",
              filter === f ? "bg-primary text-white" : "text-white/60"
            )}
          >
            {f === "ALL" ? "전체" : f}
          </button>
        ))}
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-white/50 border-b border-white/5">
              <th className="px-4 py-3 w-20">유형</th>
              <th className="px-4 py-3">사업명</th>
              <th className="px-4 py-3 w-16">버전</th>
              <th className="px-4 py-3">파일명</th>
              <th className="px-4 py-3 w-24">크기</th>
              <th className="px-4 py-3 w-44">생성일</th>
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
                생성된 산출물이 없습니다. <Link to="/generator" className="text-primary">생성기로 →</Link>
              </td></tr>
            )}
            {!loading && items.map((a) => {
              const Icon = a.type === "PPTX" ? FileText : FileSpreadsheet;
              return (
                <tr key={a.id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="px-4 py-3"><Icon size={14} className="inline mr-1 text-primary" />{a.type}</td>
                  <td className="px-4 py-3">
                    <Link to={`/projects/${a.projectUuid}`} className="text-white hover:text-primary">
                      {a.projectName}
                    </Link>
                    <div className="text-[11px] text-white/30 font-mono">{shortUuid(a.projectUuid || "")}</div>
                  </td>
                  <td className="px-4 py-3 text-white/60">v{a.version}</td>
                  <td className="px-4 py-3 font-mono text-xs">{a.filename}</td>
                  <td className="px-4 py-3 text-white/60">{formatBytes(a.sizeBytes)}</td>
                  <td className="px-4 py-3 text-xs text-white/50">{formatDate(a.createdAt)}</td>
                  <td className="px-4 py-3 text-right">
                    <button className="inline-flex p-1.5 hover:bg-white/10 rounded" onClick={() => setPreviewId(a.id)} title="미리보기">
                      <Eye size={14} />
                    </button>
                    <button className="inline-flex p-1.5 hover:bg-white/10 rounded ml-1" onClick={() => handleDownload(a)} title="다운로드">
                      <Download size={14} />
                    </button>
                    <button className="inline-flex p-1.5 hover:bg-danger/20 hover:text-danger rounded ml-1" onClick={() => handleDelete(a)} title="삭제">
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
          <button className="btn-ghost" disabled={page === 0} onClick={() => reload(page - 1, filter)}>이전</button>
          <span className="px-3 py-2 text-white/50">{page + 1} / {totalPages}</span>
          <button className="btn-ghost" disabled={page + 1 >= totalPages} onClick={() => reload(page + 1, filter)}>다음</button>
        </div>
      )}

      <ArtifactPreviewDrawer artifactId={previewId} onClose={() => setPreviewId(null)} />
    </div>
  );
}
