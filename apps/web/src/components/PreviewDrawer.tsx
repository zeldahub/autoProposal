import { useEffect, useState } from "react";
import { X, Loader2, FileText, FileSpreadsheet, File as FileIcon } from "lucide-react";
import { getFilePreview, type FilePreview } from "../api/client";
import { formatBytes } from "../lib/format";

export default function PreviewDrawer({
  mongoDocId, onClose,
}: {
  mongoDocId: string | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<FilePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!mongoDocId) return;
    setData(null); setError(null); setLoading(true);
    getFilePreview(mongoDocId)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.error?.message || "미리보기 실패"))
      .finally(() => setLoading(false));
  }, [mongoDocId]);

  if (!mongoDocId) return null;

  const Icon = data?.mimeType?.includes("pdf") ? FileText
    : data?.mimeType?.includes("word") ? FileText
    : data?.mimeType?.includes("sheet") ? FileSpreadsheet
    : FileIcon;

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div className="flex-1 bg-black/60 backdrop-blur-sm" />
      <aside
        className="w-[640px] max-w-[90vw] bg-surface border-l border-white/10 shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="px-5 py-4 border-b border-white/5 flex items-center gap-3">
          <Icon size={18} className="text-primary" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold truncate">{data?.filename || "로딩 중..."}</div>
            {data && (
              <div className="text-[11px] text-white/40 mt-0.5">
                {data.slot} · {formatBytes(data.sizeBytes)} · {data.totalChars.toLocaleString()}자 · {data.chunkCount}청크
              </div>
            )}
          </div>
          <button className="p-2 hover:bg-white/5 rounded" onClick={onClose} aria-label="닫기">
            <X size={16} />
          </button>
        </header>

        {loading && (
          <div className="flex-1 flex items-center justify-center text-white/50">
            <Loader2 className="animate-spin mr-2" size={16} /> 미리보기 로딩 중...
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center text-danger">{error}</div>
        )}

        {data && !loading && (
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {data.summary && (
              <section>
                <h3 className="text-xs font-semibold text-white/50 mb-2">요약</h3>
                <div className="text-sm text-white/80 bg-bg/60 border border-white/5 rounded p-3 whitespace-pre-line">
                  {data.summary}
                </div>
              </section>
            )}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-white/50">추출 텍스트 미리보기</h3>
                <span className="text-[10px] text-white/30">최대 8KB</span>
              </div>
              <pre className="text-xs text-white/80 bg-bg/60 border border-white/5 rounded p-3 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-[60vh] overflow-y-auto">
                {data.preview || "(텍스트 없음)"}
              </pre>
            </section>
          </div>
        )}
      </aside>
    </div>
  );
}
