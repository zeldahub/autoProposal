import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell, CheckCheck, Trash2, Loader2,
  CheckCircle2, AlertTriangle, AlertCircle, Info, Filter,
} from "lucide-react";
import clsx from "clsx";
import {
  listNotifications, markNotificationRead, markAllNotificationsRead,
  deleteNotification, deleteAllReadNotifications,
  type Notification, type NotifLevel,
} from "../api/client";
import { formatDate } from "../lib/format";
import { useToast } from "../ui/toast/ToastProvider";
import { useConfirm } from "../ui/confirm/ConfirmProvider";

const LEVEL_ICON: Record<NotifLevel, typeof Info> = {
  INFO: Info, SUCCESS: CheckCircle2, WARN: AlertTriangle, ERROR: AlertCircle,
};
const LEVEL_COLOR: Record<NotifLevel, string> = {
  INFO: "text-white/70", SUCCESS: "text-emerald-400",
  WARN: "text-yellow-400", ERROR: "text-rose-400",
};

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [loading, setLoading] = useState(false);
  const SIZE = 30;
  const toast = useToast();
  const confirm = useConfirm();
  const nav = useNavigate();

  const reload = async (p = page, unread = onlyUnread) => {
    setLoading(true);
    try {
      const r = await listNotifications({ page: p, size: SIZE, onlyUnread: unread });
      setItems(r.items);
      setTotal(r.total);
      setPage(p);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(0, onlyUnread); /* eslint-disable-next-line */ }, [onlyUnread]);

  const handleClick = async (n: Notification) => {
    if (!n.readAt) {
      await markNotificationRead(n.id);
      setItems((prev) => prev.map((x) => x.id === n.id ? { ...x, readAt: new Date().toISOString() } : x));
    }
    if (n.link) nav(n.link);
  };

  const handleMarkAll = async () => {
    const r = await markAllNotificationsRead();
    toast.success(`${r.updated}건 읽음 처리`);
    reload(page);
  };

  const handleClearRead = async () => {
    const ok = await confirm({
      title: "읽은 알림 비우기",
      message: "읽음 상태인 모든 알림을 삭제하시겠습니까?",
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    const r = await deleteAllReadNotifications();
    toast.success(`${r.deleted}건 삭제`);
    reload(0);
  };

  const handleDelete = async (id: number) => {
    await deleteNotification(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
    setTotal((t) => t - 1);
  };

  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-center gap-3">
        <Bell size={20} className="text-primary" />
        <h1 className="text-2xl font-bold">알림</h1>
        <span className="text-sm text-white/40">총 {total}건</span>
        <div className="ml-auto flex gap-2">
          <button
            className={clsx("btn-ghost", onlyUnread && "text-primary")}
            onClick={() => setOnlyUnread((v) => !v)}
          >
            <Filter size={14} className="mr-1" /> {onlyUnread ? "안읽음만" : "전체"}
          </button>
          <button className="btn-ghost" onClick={handleMarkAll}>
            <CheckCheck size={14} className="mr-1" /> 모두 읽음
          </button>
          <button className="btn-ghost" onClick={handleClearRead}>
            <Trash2 size={14} className="mr-1" /> 읽은 알림 비우기
          </button>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        {loading && (
          <div className="px-4 py-12 text-center text-white/40">
            <Loader2 className="inline animate-spin mr-2" size={14} /> 로딩 중...
          </div>
        )}
        {!loading && items.length === 0 && (
          <div className="px-4 py-16 text-center text-white/40">알림이 없습니다.</div>
        )}
        {!loading && items.map((n) => {
          const Icon = LEVEL_ICON[n.level];
          return (
            <div
              key={n.id}
              onClick={() => handleClick(n)}
              className={clsx(
                "px-5 py-4 border-b border-white/5 cursor-pointer hover:bg-white/5 group",
                !n.readAt && "bg-primary/[0.04]"
              )}
            >
              <div className="flex items-start gap-3">
                <Icon size={16} className={clsx("mt-0.5 shrink-0", LEVEL_COLOR[n.level])} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2">
                    <div className={clsx("text-sm", !n.readAt ? "font-semibold text-white" : "text-white/70")}>
                      {n.title}
                    </div>
                    <span className="text-[10px] text-white/30 uppercase tracking-wide">{n.type}</span>
                    {!n.readAt && <span className="text-[10px] text-primary">● new</span>}
                  </div>
                  {n.message && (
                    <div className="text-sm text-white/60 mt-1 break-words">{n.message}</div>
                  )}
                  <div className="text-xs text-white/30 mt-1">{formatDate(n.createdAt)}</div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(n.id); }}
                  className="opacity-0 group-hover:opacity-100 p-2 text-white/40 hover:text-rose-400 hover:bg-white/5 rounded"
                  title="삭제"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          );
        })}
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
