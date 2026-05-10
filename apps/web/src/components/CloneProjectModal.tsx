import { useEffect, useState } from "react";
import { Copy, Loader2, X } from "lucide-react";
import { cloneProject } from "../api/client";
import { useToast } from "../ui/toast/ToastProvider";

export default function CloneProjectModal({
  sourceUuid, sourceName, attachmentCount,
  open, onClose, onCloned,
}: {
  sourceUuid: string;
  sourceName: string;
  attachmentCount: number;
  open: boolean;
  onClose: () => void;
  onCloned: (newUuid: string) => void;
}) {
  const [newName, setNewName] = useState("");
  const [includeAtt, setIncludeAtt] = useState(true);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setNewName(`${sourceName} (복제)`);
      setIncludeAtt(true);
    }
  }, [open, sourceName]);

  if (!open) return null;

  const handleSubmit = async () => {
    setBusy(true);
    try {
      const r = await cloneProject(sourceUuid, {
        newName: newName.trim() || undefined,
        includeAttachments: includeAtt,
      });
      toast.success(
        r.attachmentCount > 0
          ? `복제 완료 — 첨부 ${r.attachmentCount}건 함께 복사됨`
          : "복제 완료"
      );
      onCloned(r.uuid);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "복제 실패");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-[480px] max-w-[92vw] bg-surface border border-white/10 rounded-md shadow-2xl animate-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="px-5 py-4 border-b border-white/5 flex items-center gap-2">
          <Copy size={16} className="text-primary" />
          <h3 className="text-base font-semibold">사업 복제</h3>
          <button className="ml-auto p-1 hover:bg-white/5 rounded" onClick={onClose} aria-label="닫기">
            <X size={14} />
          </button>
        </header>
        <div className="px-5 py-4 space-y-4">
          <div>
            <div className="text-xs text-white/50 mb-1">원본 사업</div>
            <div className="text-sm text-white/80 truncate">{sourceName}</div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-white/50">새 사업명</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              maxLength={200}
              autoFocus
              className="w-full px-3 py-2 text-sm bg-bg/60 border border-white/10 rounded-md focus:outline-none focus:border-primary"
            />
          </div>

          <label className="flex items-start gap-2 cursor-pointer text-sm">
            <input
              type="checkbox"
              checked={includeAtt}
              onChange={(e) => setIncludeAtt(e.target.checked)}
              className="mt-0.5"
              disabled={attachmentCount === 0}
            />
            <span className="flex-1">
              <span className={attachmentCount === 0 ? "text-white/40" : "text-white/80"}>
                첨부 파일 함께 복사 ({attachmentCount}건)
              </span>
              <span className="block text-[11px] text-white/40 mt-0.5">
                {attachmentCount === 0
                  ? "원본 사업에 첨부된 파일이 없습니다."
                  : "분석 결과 / 산출물 / LLM 호출 이력은 복제하지 않습니다."}
              </span>
            </span>
          </label>
        </div>
        <footer className="px-5 py-3 border-t border-white/5 flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose} disabled={busy}>취소</button>
          <button className="btn-primary" onClick={handleSubmit} disabled={busy || !newName.trim()}>
            {busy ? <Loader2 size={14} className="animate-spin mr-1" /> : <Copy size={14} className="mr-1" />}
            복제
          </button>
        </footer>
      </div>
    </div>
  );
}
