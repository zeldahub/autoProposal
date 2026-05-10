import { useEffect, useState } from "react";
import { Loader2, MessageCircle, Trash2, Users, X } from "lucide-react";
import {
  listProjectShares, addProjectShare, updateProjectShare, deleteProjectShare,
  listProjectComments, addProjectComment, deleteProjectComment,
  type ShareItem, type CommentItem, type ShareRole,
} from "../api/client";
import { useToast } from "../ui/toast/ToastProvider";
import { useConfirm } from "../ui/confirm/ConfirmProvider";
import { useT } from "../i18n";
import { formatDate } from "../lib/format";

export default function CollabPanel({ projectUuid, isOwner }: { projectUuid: string; isOwner: boolean }) {
  const t = useT();
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <SharePanel projectUuid={projectUuid} canManage={isOwner} t={t} />
      <CommentPanel projectUuid={projectUuid} t={t} />
    </div>
  );
}

function SharePanel({ projectUuid, canManage, t }: { projectUuid: string; canManage: boolean; t: (k: string) => string }) {
  const [shares, setShares] = useState<ShareItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ShareRole>("READ");
  const [adding, setAdding] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();

  const reload = async () => {
    setLoading(true);
    try {
      const r = await listProjectShares(projectUuid);
      setShares(r.items);
    } catch {
      // ignore (403 일 수 있음 — 공유 받은 자)
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [projectUuid]);

  const handleAdd = async () => {
    if (!email.trim()) return;
    setAdding(true);
    try {
      await addProjectShare(projectUuid, { email: email.trim(), role });
      setEmail("");
      toast.success("공유 대상이 추가되었습니다.");
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "공유 추가 실패");
    } finally {
      setAdding(false);
    }
  };

  const handleRoleChange = async (s: ShareItem, next: ShareRole) => {
    if (s.role === next) return;
    try {
      await updateProjectShare(projectUuid, s.id, next);
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "권한 변경 실패");
    }
  };

  const handleRemove = async (s: ShareItem) => {
    const ok = await confirm({
      title: "공유 해제",
      message: `${s.userEmail} 의 공유를 해제하시겠습니까?`,
      confirmLabel: "해제",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await deleteProjectShare(projectUuid, s.id);
      await reload();
      toast.success("공유가 해제되었습니다.");
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "해제 실패");
    }
  };

  return (
    <section className="card p-4 space-y-3">
      <header className="flex items-center gap-2 border-b border-white/5 pb-2">
        <Users size={14} className="text-primary" />
        <h3 className="text-sm font-semibold">{t("share.title")}</h3>
      </header>

      {canManage && (
        <div className="flex gap-2">
          <input
            type="email"
            placeholder={t("login.email")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input flex-1 text-sm"
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          />
          <select
            className="input text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value as ShareRole)}
          >
            <option value="READ">{t("share.role.read")}</option>
            <option value="EDIT">{t("share.role.edit")}</option>
          </select>
          <button className="btn-primary" disabled={adding || !email.trim()} onClick={handleAdd}>
            {adding ? <Loader2 size={14} className="animate-spin" /> : t("common.add")}
          </button>
        </div>
      )}

      {loading ? (
        <div className="text-xs text-white/40 py-3 flex items-center gap-2">
          <Loader2 size={12} className="animate-spin" /> {t("common.loading")}
        </div>
      ) : shares.length === 0 ? (
        <div className="text-xs text-white/40 py-2">{t("share.empty")}</div>
      ) : (
        <ul className="divide-y divide-white/5">
          {shares.map((s) => (
            <li key={s.id} className="py-2 flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-sm truncate">{s.userDisplayName || s.userEmail}</div>
                <div className="text-[11px] text-white/40">{s.userEmail} · {formatDate(s.createdAt)}</div>
              </div>
              {canManage ? (
                <>
                  <select
                    className="input text-xs"
                    value={s.role}
                    onChange={(e) => handleRoleChange(s, e.target.value as ShareRole)}
                  >
                    <option value="READ">{t("share.role.read")}</option>
                    <option value="EDIT">{t("share.role.edit")}</option>
                  </select>
                  <button className="p-1 text-white/40 hover:text-danger" onClick={() => handleRemove(s)}>
                    <X size={14} />
                  </button>
                </>
              ) : (
                <span className="text-xs text-white/60">{s.role}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CommentPanel({ projectUuid, t }: { projectUuid: string; t: (k: string) => string }) {
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [posting, setPosting] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();

  const reload = async () => {
    setLoading(true);
    try {
      const items = await listProjectComments(projectUuid);
      setComments(items);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [projectUuid]);

  const handlePost = async () => {
    if (!text.trim()) return;
    setPosting(true);
    try {
      await addProjectComment(projectUuid, text.trim());
      setText("");
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "댓글 작성 실패");
    } finally {
      setPosting(false);
    }
  };

  const handleDelete = async (c: CommentItem) => {
    const ok = await confirm({
      title: "댓글 삭제",
      message: "이 댓글을 삭제하시겠습니까?",
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await deleteProjectComment(projectUuid, c.id);
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "삭제 실패");
    }
  };

  return (
    <section className="card p-4 space-y-3">
      <header className="flex items-center gap-2 border-b border-white/5 pb-2">
        <MessageCircle size={14} className="text-primary" />
        <h3 className="text-sm font-semibold">{t("comment.title")}</h3>
        <span className="text-[11px] text-white/40">({comments.length})</span>
      </header>

      <div className="flex gap-2">
        <textarea
          className="input flex-1 text-sm min-h-[60px]"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("comment.placeholder")}
        />
        <button
          className="btn-primary self-stretch px-3"
          disabled={posting || !text.trim()}
          onClick={handlePost}
        >
          {posting ? <Loader2 size={14} className="animate-spin" /> : t("comment.add")}
        </button>
      </div>

      {loading ? (
        <div className="text-xs text-white/40 py-3 flex items-center gap-2">
          <Loader2 size={12} className="animate-spin" /> {t("common.loading")}
        </div>
      ) : comments.length === 0 ? (
        <div className="text-xs text-white/40 py-2">{t("comment.empty")}</div>
      ) : (
        <ul className="space-y-2">
          {comments.map((c) => (
            <li key={c.id} className="bg-bg/40 rounded p-3 text-sm">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-medium text-white/90">{c.userDisplayName || c.userEmail}</span>
                <span className="text-[11px] text-white/40">{formatDate(c.createdAt)}</span>
                <button
                  className="ml-auto text-white/30 hover:text-danger"
                  onClick={() => handleDelete(c)}
                  title={t("common.delete")}
                >
                  <Trash2 size={12} />
                </button>
              </div>
              <div className="whitespace-pre-line text-white/80">{c.body}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
