import clsx from "clsx";

const STYLES: Record<string, string> = {
  DRAFT: "bg-white/5 text-white/60",
  READY: "bg-primary/15 text-primary",
  GENERATED: "bg-accent/15 text-accent",
  ARCHIVED: "bg-white/5 text-white/40",
};

const LABELS: Record<string, string> = {
  DRAFT: "초안",
  READY: "준비",
  GENERATED: "생성됨",
  ARCHIVED: "보관",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx("inline-flex items-center text-[11px] px-2 py-0.5 rounded", STYLES[status] || "bg-white/5")}>
      {LABELS[status] || status}
    </span>
  );
}
