import { useEffect, useState } from "react";
import { Loader2, Save, KeyRound, User as UserIcon, Shield, Archive } from "lucide-react";
import {
  getMyProfile, updateMyProfile, changeMyPassword,
  exportAllProjectsZip, getExportSummary,
  type MeProfile,
} from "../api/client";
import { downloadBlob, formatDate } from "../lib/format";
import { useToast } from "../ui/toast/ToastProvider";
import { useAuth } from "../auth/context";

export default function Profile() {
  const [me, setMe] = useState<MeProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [displayName, setDisplayName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [savingPw, setSavingPw] = useState(false);

  const toast = useToast();
  const { refreshUser } = useAuth();

  useEffect(() => {
    setLoading(true);
    getMyProfile()
      .then((m) => {
        setMe(m);
        setDisplayName(m.displayName || "");
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSaveProfile = async () => {
    if (!me) return;
    setSavingProfile(true);
    try {
      const next = await updateMyProfile({ displayName });
      setMe(next);
      await refreshUser();
      toast.success("프로필이 저장되었습니다.");
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "저장 실패");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async () => {
    if (!pw.current || !pw.next) {
      toast.warning("현재/새 비밀번호를 모두 입력하세요.");
      return;
    }
    if (pw.next.length < 6) {
      toast.warning("새 비밀번호는 6자 이상이어야 합니다.");
      return;
    }
    if (pw.next !== pw.confirm) {
      toast.warning("새 비밀번호와 확인이 일치하지 않습니다.");
      return;
    }
    setSavingPw(true);
    try {
      await changeMyPassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      toast.success("비밀번호가 변경되었습니다.");
    } catch (e: any) {
      const msg = e?.response?.data?.error?.message || "변경 실패";
      toast.error(msg);
    } finally {
      setSavingPw(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-white/50">
        <Loader2 className="animate-spin mr-2" size={16} /> 로딩 중...
      </div>
    );
  }

  if (!me) {
    return <div className="text-white/50">프로필을 불러올 수 없습니다.</div>;
  }

  const dirty = (displayName || "") !== (me.displayName || "");

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">내 프로필</h1>
        <span className="text-sm text-white/40">계정 정보 및 보안 설정</span>
      </div>

      <section className="card p-5 space-y-4">
        <header className="flex items-center gap-2 border-b border-white/5 pb-3">
          <UserIcon size={16} className="text-primary" />
          <h2 className="text-base font-semibold">계정 정보</h2>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="text-xs text-white/50">이메일</div>
          <div className="sm:col-span-2 text-sm font-mono">{me.email}</div>

          <div className="text-xs text-white/50">권한</div>
          <div className="sm:col-span-2 text-sm flex items-center gap-1.5">
            {me.role === "ADMIN" && <Shield size={12} className="text-primary" />}
            <span className={me.role === "ADMIN" ? "text-primary font-medium" : ""}>{me.role}</span>
          </div>

          <div className="text-xs text-white/50">UUID</div>
          <div className="sm:col-span-2 text-xs text-white/40 font-mono break-all">{me.uuid}</div>

          <div className="text-xs text-white/50">가입일</div>
          <div className="sm:col-span-2 text-xs text-white/60">{formatDate(me.createdAt)}</div>

          <div className="text-xs text-white/50">최근 로그인</div>
          <div className="sm:col-span-2 text-xs text-white/60">
            {me.lastLoginAt ? formatDate(me.lastLoginAt) : <span className="text-white/30">기록 없음</span>}
          </div>
        </div>

        <div className="border-t border-white/5 pt-4 space-y-2">
          <label className="text-xs text-white/50">표시 이름</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="예: 홍길동"
            maxLength={100}
            className="w-full px-3 py-2 text-sm bg-bg/60 border border-white/10 rounded-md focus:outline-none focus:border-primary"
          />
          <div className="flex justify-end">
            <button
              className="btn-primary"
              disabled={!dirty || savingProfile}
              onClick={handleSaveProfile}
            >
              {savingProfile ? <Loader2 size={14} className="animate-spin mr-1" /> : <Save size={14} className="mr-1" />}
              저장
            </button>
          </div>
        </div>
      </section>

      <section className="card p-5 space-y-3">
        <header className="flex items-center gap-2 border-b border-white/5 pb-3">
          <Archive size={16} className="text-primary" />
          <h2 className="text-base font-semibold">데이터 백업</h2>
        </header>
        <p className="text-xs text-white/50">
          본인 소유의 모든 사업(첨부 파일/산출물/댓글/분석/LLM 세션 포함)을 zip 파일 한 개로 내려받습니다.
        </p>
        <BackupAllButton />
      </section>

      <section className="card p-5 space-y-4">
        <header className="flex items-center gap-2 border-b border-white/5 pb-3">
          <KeyRound size={16} className="text-primary" />
          <h2 className="text-base font-semibold">비밀번호 변경</h2>
        </header>

        <div className="space-y-3">
          <div className="space-y-1">
            <label className="text-xs text-white/50">현재 비밀번호</label>
            <input
              type="password"
              autoComplete="current-password"
              value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })}
              className="w-full px-3 py-2 text-sm bg-bg/60 border border-white/10 rounded-md focus:outline-none focus:border-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50">새 비밀번호 (6자 이상)</label>
            <input
              type="password"
              autoComplete="new-password"
              value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })}
              className="w-full px-3 py-2 text-sm bg-bg/60 border border-white/10 rounded-md focus:outline-none focus:border-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50">새 비밀번호 확인</label>
            <input
              type="password"
              autoComplete="new-password"
              value={pw.confirm}
              onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
              className="w-full px-3 py-2 text-sm bg-bg/60 border border-white/10 rounded-md focus:outline-none focus:border-primary"
            />
          </div>
          <div className="flex justify-end pt-1">
            <button
              className="btn-primary"
              disabled={savingPw || !pw.current || !pw.next || !pw.confirm}
              onClick={handleChangePassword}
            >
              {savingPw ? <Loader2 size={14} className="animate-spin mr-1" /> : <KeyRound size={14} className="mr-1" />}
              비밀번호 변경
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function BackupAllButton() {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<{ projectCount: number } | null>(null);
  const toast = useToast();

  useEffect(() => {
    getExportSummary().then(setSummary).catch(() => undefined);
  }, []);

  const handleBackup = async () => {
    setLoading(true);
    try {
      const r = await exportAllProjectsZip();
      const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 16);
      downloadBlob(r.data, `lon-backup-${ts}.zip`);
      toast.success("백업이 다운로드되었습니다.");
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "백업 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-between">
      <div className="text-xs text-white/50">
        대상 사업: <span className="text-white/80 font-medium">{summary?.projectCount ?? "..."}</span> 개
      </div>
      <button
        className="btn-primary"
        disabled={loading || (summary?.projectCount ?? 1) === 0}
        onClick={handleBackup}
      >
        {loading ? <Loader2 size={14} className="animate-spin mr-1" /> : <Archive size={14} className="mr-1" />}
        전체 백업 (zip)
      </button>
    </div>
  );
}
