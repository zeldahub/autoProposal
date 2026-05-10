import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bell, Check, CheckCheck, Trash2, Loader2, X,
  CheckCircle2, AlertTriangle, AlertCircle, Info,
} from "lucide-react";
import clsx from "clsx";
import {
  listNotifications, fetchUnreadCount,
  markNotificationRead, markAllNotificationsRead,
  deleteNotification, deleteAllReadNotifications,
  type Notification, type NotifLevel,
} from "../api/client";
import { formatDate } from "../lib/format";

const POLL_MS = 30_000;

const LEVEL_ICON: Record<NotifLevel, typeof Info> = {
  INFO: Info,
  SUCCESS: CheckCircle2,
  WARN: AlertTriangle,
  ERROR: AlertCircle,
};
const LEVEL_COLOR: Record<NotifLevel, string> = {
  INFO: "text-white/70",
  SUCCESS: "text-emerald-400",
  WARN: "text-yellow-400",
  ERROR: "text-rose-400",
};

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const nav = useNavigate();

  const refreshCount = async () => {
    try {
      setUnread(await fetchUnreadCount());
    } catch {
      /* 인증 만료 등은 인터셉터가 처리 */
    }
  };

  const loadList = async () => {
    setLoading(true);
    try {
      const r = await listNotifications({ page: 0, size: 20 });
      setItems(r.items);
    } finally {
      setLoading(false);
    }
  };

  // 폴링
  useEffect(() => {
    refreshCount();
    const t = setInterval(refreshCount, POLL_MS);
    return () => clearInterval(t);
  }, []);

  // 열릴 때마다 목록 새로고침
  useEffect(() => {
    if (open) loadList();
  }, [open]);

  // 외부 클릭 닫기
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const handleClickItem = async (n: Notification) => {
    if (!n.readAt) {
      await markNotificationRead(n.id);
      setItems((prev) => prev.map((x) => x.id === n.id ? { ...x, readAt: new Date().toISOString() } : x));
      setUnread((c) => Math.max(0, c - 1));
    }
    if (n.link) {
      setOpen(false);
      nav(n.link);
    }
  };

  const handleMarkAll = async () => {
    const r = await markAllNotificationsRead();
    if (r.updated > 0) {
      setItems((prev) => prev.map((x) => x.readAt ? x : { ...x, readAt: new Date().toISOString() }));
      setUnread(0);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteNotification(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
    refreshCount();
  };

  const handleClearRead = async () => {
    const r = await deleteAllReadNotifications();
    if (r.deleted > 0) {
      setItems((prev) => prev.filter((x) => !x.readAt));
    }
  };

  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-md hover:bg-white/5 text-white/70"
        aria-label="알림"
        title="알림"
      >
        <Bell size={16} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-rose-500 text-white text-[10px] font-semibold flex items-center justify-center">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-[400px] max-w-[90vw] bg-surface border border-white/10 rounded-md shadow-2xl z-40 overflow-hidden animate-modal">
          <div className="px-4 py-3 border-b border-white/5 flex items-center gap-2">
            <Bell size={14} className="text-primary" />
            <h3 className="text-sm font-semibold">알림</h3>
            <span className="text-xs text-white/40">{unread > 0 ? `${unread}개 안읽음` : "모두 읽음"}</span>
            <div className="ml-auto flex items-center gap-1">
              {unread > 0 && (
                <button
                  className="px-2 py-1 text-xs text-white/60 hover:bg-white/5 rounded inline-flex items-center"
                  onClick={handleMarkAll}
                  title="모두 읽음"
                >
                  <CheckCheck size={12} className="mr-1" /> 모두 읽음
                </button>
              )}
              <button className="p-1 text-white/60 hover:bg-white/5 rounded" onClick={() => setOpen(false)} aria-label="닫기">
                <X size={14} />
              </button>
            </div>
          </div>

          <div className="max-h-[60vh] overflow-y-auto">
            {loading && (
              <div className="px-4 py-8 text-center text-white/40 text-sm">
                <Loader2 className="inline animate-spin mr-2" size={14} /> 로딩 중...
              </div>
            )}
            {!loading && items.length === 0 && (
              <div className="px-4 py-12 text-center text-white/40 text-sm">알림이 없습니다.</div>
            )}
            {!loading && items.map((n) => {
              const Icon = LEVEL_ICON[n.level];
              return (
                <div
                  key={n.id}
                  onClick={() => handleClickItem(n)}
                  className={clsx(
                    "px-4 py-3 border-b border-white/5 cursor-pointer hover:bg-white/5 group",
                    !n.readAt && "bg-primary/[0.03]"
                  )}
                >
                  <div className="flex items-start gap-2">
                    <Icon size={14} className={clsx("mt-0.5 shrink-0", LEVEL_COLOR[n.level])} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2">
                        <div className={clsx("text-sm truncate", !n.readAt ? "font-semibold text-white" : "text-white/70")}>
                          {n.title}
                        </div>
                        <span className="text-[10px] text-white/30 uppercase tracking-wide shrink-0">{n.type}</span>
                      </div>
                      {n.message && (
                        <div className="text-xs text-white/50 mt-1 break-words">{n.message}</div>
                      )}
                      <div className="text-[11px] text-white/30 mt-1">{formatDate(n.createdAt)}</div>
                    </div>
                    <button
                      onClick={(e) => handleDelete(n.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-white/40 hover:text-rose-400 hover:bg-white/5 rounded transition"
                      title="삭제"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {items.length > 0 && (
            <div className="px-3 py-2 border-t border-white/5 flex items-center gap-2 text-xs">
              <button
                className="text-white/50 hover:text-white/80"
                onClick={handleClearRead}
                title="읽은 알림 비우기"
              >
                <Check size={11} className="inline mr-1" /> 읽은 알림 비우기
              </button>
              <Link
                to="/notifications"
                onClick={() => setOpen(false)}
                className="ml-auto text-primary hover:underline"
              >
                전체 보기 →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
