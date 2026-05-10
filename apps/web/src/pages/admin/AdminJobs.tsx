import { useEffect, useRef, useState } from "react";
import {
  Play, Pause, RefreshCw, CheckCircle2, AlertCircle, Loader2, Activity,
} from "lucide-react";
import clsx from "clsx";
import {
  adminListJobs, adminRunJob, adminPauseJob, adminResumeJob,
  type JobItem, type JobRun,
} from "../../api/client";
import { formatDate } from "../../lib/format";
import { useToast } from "../../ui/toast/ToastProvider";

const REFRESH_MS = 5000;

export default function AdminJobs() {
  const [items, setItems] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const toast = useToast();
  const refreshTimer = useRef<number | null>(null);

  const reload = async () => {
    try {
      setItems(await adminListJobs());
    } finally { setLoading(false); }
  };

  useEffect(() => {
    reload();
    refreshTimer.current = window.setInterval(reload, REFRESH_MS);
    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, []);

  const runNow = async (id: string) => {
    setBusyId(id);
    try {
      const r = await adminRunJob(id);
      const last = r.lastRun;
      if (last.status === "OK") {
        toast.success(`${id} 실행 완료 · ${last.durationMs}ms`);
      } else {
        toast.error(`${id} 실패: ${last.error || "?"}`);
      }
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "실행 실패");
    } finally { setBusyId(null); }
  };

  const togglePause = async (j: JobItem) => {
    setBusyId(j.id);
    try {
      if (j.paused) {
        await adminResumeJob(j.id);
        toast.success(`${j.id} 재개`);
      } else {
        await adminPauseJob(j.id);
        toast.info(`${j.id} 일시정지`);
      }
      await reload();
    } finally { setBusyId(null); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity size={20} className="text-primary" /> 잡 모니터
        </h1>
        <span className="text-sm text-white/40">총 {items.length}개 · {REFRESH_MS / 1000}s 자동 새로고침</span>
        <button className="btn-ghost ml-auto" onClick={reload} disabled={loading}>
          <RefreshCw size={14} className={clsx("mr-1", loading && "animate-spin")} />새로고침
        </button>
      </div>

      <div className="text-xs text-white/50 bg-surface/40 border border-white/5 rounded-md px-4 py-3">
        백그라운드 잡은 BE 부팅 시 자동 시작되며, 이 화면에서 즉시 실행 / 일시정지 / 이력 확인이 가능합니다.
        AsyncIOScheduler 단일 인스턴스 + in-memory 이력 (최근 20건).
      </div>

      {items.map((j) => (
        <section key={j.id} className="card">
          <header className="flex items-center gap-3 mb-3">
            <div className={clsx(
              "w-2 h-2 rounded-full",
              j.paused ? "bg-white/30" : "bg-accent animate-pulse",
            )} />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold">{j.label}</h2>
                <code className="text-[11px] font-mono text-white/40">{j.id}</code>
                {j.paused && <span className="text-[10px] bg-white/5 text-white/60 px-1.5 py-0.5 rounded">일시정지</span>}
              </div>
              <div className="text-xs text-white/50 mt-0.5">{j.description}</div>
            </div>
            <div className="text-xs text-right text-white/50">
              <div>주기 {j.intervalMin}분</div>
              <div>다음: {formatDate(j.nextRunAt) || "—"}</div>
            </div>
            <div className="flex gap-1.5">
              <button
                className="btn-ghost"
                disabled={busyId === j.id}
                onClick={() => runNow(j.id)}
                title="즉시 실행"
              >
                {busyId === j.id ? <Loader2 className="animate-spin mr-1" size={14} /> : <Play size={14} className="mr-1" />}
                실행
              </button>
              <button
                className="btn-ghost"
                disabled={busyId === j.id}
                onClick={() => togglePause(j)}
                title={j.paused ? "재개" : "일시정지"}
              >
                {j.paused ? <Play size={14} className="mr-1" /> : <Pause size={14} className="mr-1" />}
                {j.paused ? "재개" : "정지"}
              </button>
            </div>
          </header>

          <div>
            <div className="text-[11px] font-semibold text-white/40 mb-1.5">최근 실행 이력</div>
            {j.history.length === 0 ? (
              <div className="text-xs text-white/40 text-center py-4 border border-dashed border-white/10 rounded">
                아직 실행 이력이 없습니다.
              </div>
            ) : (
              <div className="space-y-1">
                {j.history.slice(0, 5).map((r, i) => (
                  <RunRow key={i} run={r} />
                ))}
              </div>
            )}
          </div>
        </section>
      ))}
    </div>
  );
}

function RunRow({ run }: { run: JobRun }) {
  const isOK = run.status === "OK";
  const isRunning = run.status === "RUNNING";
  const Icon = isRunning ? Loader2 : isOK ? CheckCircle2 : AlertCircle;
  const color = isRunning ? "text-primary" : isOK ? "text-accent" : "text-danger";

  return (
    <div className="flex items-start gap-2 text-xs px-2 py-1.5 bg-bg/50 border border-white/5 rounded">
      <Icon size={12} className={clsx("mt-0.5 shrink-0", color, isRunning && "animate-spin")} />
      <div className="w-44 shrink-0 text-white/50">{formatDate(run.at)}</div>
      <div className="w-16 shrink-0 text-white/60">
        {run.durationMs != null ? `${run.durationMs}ms` : "—"}
      </div>
      <div className="flex-1 min-w-0 break-words">
        {isOK && run.result && (
          <code className="text-white/70 font-mono">{JSON.stringify(run.result)}</code>
        )}
        {!isOK && run.error && (
          <span className="text-danger">{run.error}</span>
        )}
      </div>
    </div>
  );
}
