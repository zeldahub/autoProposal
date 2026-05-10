import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ko } from "./ko";
import { en } from "./en";

export type Locale = "ko" | "en";
export type Dict = Record<string, string>;

const DICTS: Record<Locale, Dict> = { ko, en };

const KEY = "lon.locale";

export function detectInitial(): Locale {
  if (typeof localStorage !== "undefined") {
    const v = localStorage.getItem(KEY);
    if (v === "ko" || v === "en") return v;
  }
  if (typeof navigator !== "undefined") {
    const lang = (navigator.language || "").toLowerCase();
    if (lang.startsWith("en")) return "en";
  }
  return "ko";
}

export type I18nCtx = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
};

const Ctx = createContext<I18nCtx | null>(null);

function format(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_m, k) => (k in params ? String(params[k]) : `{${k}}`));
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectInitial);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try { localStorage.setItem(KEY, l); } catch { /* ignore */ }
  }, []);

  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    const dict = DICTS[locale] || DICTS.ko;
    const fallback = DICTS.ko;
    const raw = dict[key] ?? fallback[key] ?? key;
    return format(raw, params);
  }, [locale]);

  const value = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}

export function useT() {
  return useI18n().t;
}
