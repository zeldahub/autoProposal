import clsx from "clsx";

export default function ConfidenceBar({ value }: { value: number | undefined | null }) {
  if (value == null || isNaN(value as number)) {
    return <span className="text-[10px] text-white/30">—</span>;
  }
  const pct = Math.max(0, Math.min(1, value));
  const tier = pct >= 0.7 ? "high" : pct >= 0.4 ? "med" : "low";
  const colorBar = tier === "high" ? "bg-accent" : tier === "med" ? "bg-primary" : "bg-danger/70";
  const colorText = tier === "high" ? "text-accent" : tier === "med" ? "text-primary" : "text-danger";
  return (
    <div className="flex items-center gap-1.5" title={`신뢰도 ${(pct * 100).toFixed(0)}%`}>
      <div className="flex-1 min-w-[36px] h-1.5 bg-white/5 rounded overflow-hidden">
        <div className={clsx("h-full rounded transition-all", colorBar)} style={{ width: `${pct * 100}%` }} />
      </div>
      <span className={clsx("text-[10px] tabular-nums w-8 text-right", colorText)}>
        {(pct * 100).toFixed(0)}%
      </span>
    </div>
  );
}
