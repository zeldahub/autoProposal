import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { CheckCircle2, Info, AlertCircle, AlertTriangle, X } from "lucide-react";
import clsx from "clsx";
import type { ToastInput, ToastItem, ToastVariant } from "./types";
import { setEmitter } from "./bus";

type ToastContextValue = {
  show: (input: ToastInput) => number;
  info: (message: string, durationMs?: number) => number;
  success: (message: string, durationMs?: number) => number;
  warning: (message: string, durationMs?: number) => number;
  error: (message: string, durationMs?: number) => number;
  dismiss: (id: number) => void;
};

const Ctx = createContext<ToastContextValue | null>(null);

const VARIANT_STYLES: Record<ToastVariant, { bar: string; Icon: any; iconColor: string }> = {
  info:    { bar: "bg-primary",  Icon: Info,         iconColor: "text-primary" },
  success: { bar: "bg-accent",   Icon: CheckCircle2, iconColor: "text-accent" },
  warning: { bar: "bg-yellow-500", Icon: AlertTriangle, iconColor: "text-yellow-500" },
  error:   { bar: "bg-danger",   Icon: AlertCircle,  iconColor: "text-danger" },
};

const DEFAULT_DURATION = 3500;
const MAX_VISIBLE = 5;

let _seq = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<number, number>>(new Map());

  const dismiss = useCallback((id: number) => {
    setItems((cur) => cur.filter((t) => t.id !== id));
    const tm = timersRef.current.get(id);
    if (tm) {
      clearTimeout(tm);
      timersRef.current.delete(id);
    }
  }, []);

  const show = useCallback((input: ToastInput): number => {
    const id = _seq++;
    const item: ToastItem = {
      id,
      createdAt: Date.now(),
      variant: input.variant || "info",
      durationMs: input.durationMs ?? DEFAULT_DURATION,
      message: input.message,
      description: input.description,
    };
    setItems((cur) => {
      const next = [...cur, item];
      // 한도 초과 시 오래된 것부터 제거
      while (next.length > MAX_VISIBLE) {
        const dropped = next.shift();
        if (dropped) {
          const tm = timersRef.current.get(dropped.id);
          if (tm) { clearTimeout(tm); timersRef.current.delete(dropped.id); }
        }
      }
      return next;
    });
    if (item.durationMs && item.durationMs > 0) {
      const tm = window.setTimeout(() => dismiss(id), item.durationMs);
      timersRef.current.set(id, tm);
    }
    return id;
  }, [dismiss]);

  const value = useMemo<ToastContextValue>(() => ({
    show,
    info:    (m, d) => show({ message: m, variant: "info", durationMs: d }),
    success: (m, d) => show({ message: m, variant: "success", durationMs: d }),
    warning: (m, d) => show({ message: m, variant: "warning", durationMs: d }),
    error:   (m, d) => show({ message: m, variant: "error", durationMs: d }),
    dismiss,
  }), [show, dismiss]);

  // bus.ts 의 _emit 에 주입 → axios interceptor 등이 toastBus.error(...) 호출 가능
  useEffect(() => {
    setEmitter((input) => show(input));
    return () => { setEmitter(() => -1); };
  }, [show]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 pointer-events-none w-[360px] max-w-[90vw]">
        {items.map((t) => {
          const style = VARIANT_STYLES[t.variant || "info"];
          const Icon = style.Icon;
          return (
            <div
              key={t.id}
              className="pointer-events-auto bg-surface border border-white/10 rounded-md shadow-xl overflow-hidden flex animate-toast"
            >
              <div className={clsx("w-1 shrink-0", style.bar)} />
              <div className="flex-1 px-3 py-2.5 flex gap-2.5">
                <Icon size={16} className={clsx("mt-0.5 shrink-0", style.iconColor)} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm leading-5 break-words">{t.message}</div>
                  {t.description && (
                    <div className="text-[11px] text-white/50 mt-0.5 break-words">{t.description}</div>
                  )}
                </div>
                <button
                  onClick={() => dismiss(t.id)}
                  className="text-white/30 hover:text-white/70 shrink-0"
                  aria-label="닫기"
                >
                  <X size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </Ctx.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
