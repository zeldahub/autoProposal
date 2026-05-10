import { useEffect, useState } from "react";
import {
  Plus, Trash2, Power, CheckCircle2, AlertCircle,
  Loader2, KeyRound, RefreshCw,
} from "lucide-react";
import clsx from "clsx";
import {
  listAiSettings, createAiSetting, updateAiSetting,
  deleteAiSetting, testAiSetting,
  type AiSetting,
} from "../api/client";
import { formatDate } from "../lib/format";
import { useConfirm } from "../ui/confirm/ConfirmProvider";
import { useToast } from "../ui/toast/ToastProvider";

const PROVIDERS: { id: AiSetting["provider"]; label: string; defaultModel: string }[] = [
  { id: "OPENAI", label: "ChatGPT (OpenAI)", defaultModel: "gpt-4o-mini" },
  { id: "GEMINI", label: "Google Gemini", defaultModel: "gemini-2.5-flash" },
  { id: "ANTHROPIC", label: "Claude (Anthropic)", defaultModel: "claude-sonnet-4-6" },
];

export default function SettingsAi() {
  const [items, setItems] = useState<AiSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [openProvider, setOpenProvider] = useState<AiSetting["provider"] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [testStatus, setTestStatus] = useState<Record<number, { ok: boolean; msg: string }>>({});
  const toast = useToast();
  const confirm = useConfirm();

  // 신규 폼
  const [form, setForm] = useState({
    provider: "GEMINI" as AiSetting["provider"],
    alias: "",
    apiKey: "",
    defaultModel: "gemini-2.5-flash",
    temperature: 0.4,
    isActive: true,
  });

  const reload = async () => {
    setLoading(true);
    try {
      setItems(await listAiSettings());
    } finally { setLoading(false); }
  };

  useEffect(() => { reload(); }, []);

  const openAdd = (provider: AiSetting["provider"]) => {
    const meta = PROVIDERS.find((p) => p.id === provider)!;
    setForm({ provider, alias: "", apiKey: "", defaultModel: meta.defaultModel, temperature: 0.4, isActive: true });
    setOpenProvider(provider);
  };

  const handleAdd = async () => {
    if (!form.apiKey || form.apiKey.length < 10) {
      toast.warning("API Key를 10자 이상 입력하세요");
      return;
    }
    try {
      await createAiSetting({
        provider: form.provider,
        alias: form.alias || undefined,
        apiKey: form.apiKey,
        defaultModel: form.defaultModel || undefined,
        temperature: form.temperature,
        isActive: form.isActive,
      });
      setOpenProvider(null);
      await reload();
      toast.success("키 등록 완료");
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "등록 실패");
    }
  };

  const handleDelete = async (s: AiSetting) => {
    const ok = await confirm({
      title: "AI 키 삭제",
      message: `${s.provider}${s.alias ? ` · ${s.alias}` : ""} 키를 삭제하시겠습니까?`,
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    setBusyId(s.id);
    try {
      await deleteAiSetting(s.id);
      toast.success("키가 삭제되었습니다.");
      await reload();
    } finally { setBusyId(null); }
  };

  const handleToggleActive = async (s: AiSetting) => {
    setBusyId(s.id);
    try {
      await updateAiSetting(s.id, { isActive: !s.isActive });
      await reload();
    } finally { setBusyId(null); }
  };

  const handleTest = async (s: AiSetting) => {
    setBusyId(s.id);
    setTestStatus((cur) => ({ ...cur, [s.id]: { ok: true, msg: "검증 중..." } }));
    try {
      const r = await testAiSetting(s.id);
      setTestStatus((cur) => ({ ...cur, [s.id]: { ok: true, msg: `OK · ${r.latencyMs}ms` } }));
      await reload();
    } catch (e: any) {
      const msg = e?.response?.data?.error?.message || "검증 실패";
      setTestStatus((cur) => ({ ...cur, [s.id]: { ok: false, msg } }));
    } finally { setBusyId(null); }
  };

  const grouped: Record<string, AiSetting[]> = {};
  PROVIDERS.forEach((p) => (grouped[p.id] = []));
  items.forEach((s) => grouped[s.provider]?.push(s));

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">AI Provider · API 키 관리</h1>
        <span className="text-sm text-white/40">{items.length}건 저장됨</span>
        <button className="btn-ghost ml-auto" onClick={reload}>
          <RefreshCw size={14} className="mr-1" />새로고침
        </button>
      </div>

      <div className="text-xs text-white/50 bg-surface/40 border border-white/5 rounded-md px-4 py-3">
        등록된 키는 AES-256-GCM으로 서버에 암호화 저장되며, 응답에는 마스킹된 미리보기만 노출됩니다.
        <span className="text-accent ml-1">활성</span>으로 설정한 키는 분석/생성 호출 시 자동 사용됩니다.
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-white/50"><Loader2 className="animate-spin" size={16} /> 로딩 중...</div>
      ) : (
        PROVIDERS.map((p) => (
          <section key={p.id} className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="section-title m-0"><KeyRound size={16} className="text-primary" /> {p.label}</h2>
              <button className="btn-ghost" onClick={() => openAdd(p.id)}>
                <Plus size={14} className="mr-1" />키 추가
              </button>
            </div>

            {(grouped[p.id] || []).length === 0 ? (
              <div className="text-sm text-white/40 text-center py-6 border border-dashed border-white/10 rounded">
                등록된 키 없음
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-white/50 border-b border-white/5">
                    <th className="px-2 py-2 w-32">별칭</th>
                    <th className="px-2 py-2 w-44">키</th>
                    <th className="px-2 py-2 w-44">기본 모델</th>
                    <th className="px-2 py-2 w-20">온도</th>
                    <th className="px-2 py-2 w-20">상태</th>
                    <th className="px-2 py-2 w-44">최근 검증</th>
                    <th className="px-2 py-2 w-44"></th>
                  </tr>
                </thead>
                <tbody>
                  {(grouped[p.id] || []).map((s) => {
                    const ts = testStatus[s.id];
                    return (
                      <tr key={s.id} className="border-b border-white/5 hover:bg-white/5">
                        <td className="px-2 py-2">{s.alias || <span className="text-white/30">-</span>}</td>
                        <td className="px-2 py-2 font-mono text-xs">{s.keyPreview}</td>
                        <td className="px-2 py-2 text-xs">{s.defaultModel || "-"}</td>
                        <td className="px-2 py-2 text-xs text-white/60">{s.temperature ?? "-"}</td>
                        <td className="px-2 py-2">
                          <button
                            onClick={() => handleToggleActive(s)}
                            disabled={busyId === s.id}
                            className={clsx(
                              "inline-flex items-center text-[11px] px-2 py-0.5 rounded",
                              s.isActive ? "bg-accent/15 text-accent" : "bg-white/5 text-white/40"
                            )}
                          >
                            <Power size={10} className="mr-1" />{s.isActive ? "활성" : "비활성"}
                          </button>
                        </td>
                        <td className="px-2 py-2 text-xs text-white/50">
                          {ts ? (
                            <span className={ts.ok ? "text-accent" : "text-danger"}>
                              {ts.ok ? <CheckCircle2 size={11} className="inline mr-1" /> : <AlertCircle size={11} className="inline mr-1" />}
                              {ts.msg}
                            </span>
                          ) : (
                            formatDate(s.lastVerifiedAt)
                          )}
                        </td>
                        <td className="px-2 py-2 text-right">
                          <button
                            className="btn-ghost text-xs"
                            disabled={busyId === s.id}
                            onClick={() => handleTest(s)}
                          >
                            {busyId === s.id ? <Loader2 size={12} className="animate-spin" /> : "연결 테스트"}
                          </button>
                          <button
                            className="inline-flex p-1.5 hover:bg-danger/20 hover:text-danger rounded ml-1"
                            disabled={busyId === s.id}
                            onClick={() => handleDelete(s)}
                            title="삭제"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}

            {openProvider === p.id && (
              <div className="mt-4 border border-white/10 rounded-md p-4 bg-bg/50">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">별칭 (선택)</label>
                    <input className="input" value={form.alias}
                      onChange={(e) => setForm({ ...form, alias: e.target.value })}
                      placeholder="예: 회사 공용 키" />
                  </div>
                  <div>
                    <label className="label">기본 모델</label>
                    <input className="input" value={form.defaultModel}
                      onChange={(e) => setForm({ ...form, defaultModel: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <label className="label">API Key</label>
                    <input className="input" type="password" value={form.apiKey}
                      onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
                      placeholder="••••••••••" autoFocus />
                  </div>
                  <div>
                    <label className="label">온도 (0 ~ 2)</label>
                    <input className="input" type="number" step={0.1} min={0} max={2}
                      value={form.temperature}
                      onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={form.isActive}
                        onChange={(e) => setForm({ ...form, isActive: e.target.checked })} />
                      활성화
                    </label>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button className="btn-primary" onClick={handleAdd}>저장</button>
                  <button className="btn-ghost" onClick={() => setOpenProvider(null)}>취소</button>
                </div>
              </div>
            )}
          </section>
        ))
      )}

    </div>
  );
}
