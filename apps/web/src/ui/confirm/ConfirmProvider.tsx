import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import clsx from "clsx";

export type ConfirmVariant = "info" | "warning" | "danger";

export type ConfirmOptions = {
  title?: string;
  message: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
};

type ConfirmFn = (opts: ConfirmOptions) => Promise<boolean>;

const Ctx = createContext<ConfirmFn | null>(null);

const VARIANT_STYLES: Record<ConfirmVariant, { Icon: any; iconBg: string; iconColor: string; btn: string }> = {
  info:    { Icon: Info,           iconBg: "bg-primary/15",  iconColor: "text-primary",  btn: "btn-primary" },
  warning: { Icon: AlertTriangle,  iconBg: "bg-yellow-500/15", iconColor: "text-yellow-500", btn: "btn-primary" },
  danger:  { Icon: AlertCircle,    iconBg: "bg-danger/15",   iconColor: "text-danger",   btn: "btn bg-danger hover:bg-danger/90 text-white" },
};

type Pending = ConfirmOptions & { resolve: (v: boolean) => void };

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<Pending | null>(null);
  const cancelBtnRef = useRef<HTMLButtonElement>(null);

  const confirm = useCallback<ConfirmFn>((opts) => {
    return new Promise<boolean>((resolve) => {
      setPending({ ...opts, resolve });
    });
  }, []);

  const close = (ok: boolean) => {
    if (pending) {
      pending.resolve(ok);
      setPending(null);
    }
  };

  // ESC = cancel, Enter = confirm
  useEffect(() => {
    if (!pending) return;
    cancelBtnRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close(false);
      if (e.key === "Enter") close(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  const value = useMemo(() => confirm, [confirm]);

  const variant = pending?.variant || "info";
  const style = VARIANT_STYLES[variant];
  const Icon = style?.Icon;

  return (
    <Ctx.Provider value={value}>
      {children}
      {pending && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={() => close(false)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="bg-surface border border-white/10 rounded-lg shadow-2xl w-full max-w-md animate-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 flex gap-4">
              <div className={clsx("w-10 h-10 rounded-full flex items-center justify-center shrink-0", style.iconBg)}>
                <Icon className={style.iconColor} size={20} />
              </div>
              <div className="flex-1 min-w-0">
                {pending.title && (
                  <h3 className="text-base font-semibold mb-1">{pending.title}</h3>
                )}
                <p className="text-sm text-white/80 whitespace-pre-line">{pending.message}</p>
                {pending.description && (
                  <p className="text-xs text-white/50 mt-2 whitespace-pre-line">{pending.description}</p>
                )}
              </div>
            </div>
            <div className="px-5 pb-5 flex justify-end gap-2">
              <button
                ref={cancelBtnRef}
                className="btn-ghost"
                onClick={() => close(false)}
              >
                {pending.cancelLabel || "취소"}
              </button>
              <button
                className={style.btn}
                onClick={() => close(true)}
              >
                {pending.confirmLabel || "확인"}
              </button>
            </div>
          </div>
        </div>
      )}
    </Ctx.Provider>
  );
}

export function useConfirm(): ConfirmFn {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useConfirm must be used within ConfirmProvider");
  return ctx;
}
