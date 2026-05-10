import { useI18n } from "../i18n";
import { Languages } from "lucide-react";
import clsx from "clsx";

export default function LangToggle({ className }: { className?: string }) {
  const { locale, setLocale } = useI18n();
  return (
    <div className={clsx("flex items-center gap-1 text-xs", className)}>
      <Languages size={13} className="text-white/40" />
      {(["ko", "en"] as const).map((l) => (
        <button
          key={l}
          onClick={() => setLocale(l)}
          className={clsx(
            "px-2 py-1 rounded transition",
            locale === l ? "bg-primary/15 text-primary" : "text-white/50 hover:bg-white/5",
          )}
        >
          {l === "ko" ? "KO" : "EN"}
        </button>
      ))}
    </div>
  );
}
