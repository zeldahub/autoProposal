import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bot, Upload, Sparkles, FileSpreadsheet, FileText,
  CheckCircle2, AlertCircle, Loader2, KeyRound,
} from "lucide-react";
import clsx from "clsx";
import {
  llmTest, listCategories, createProject, analyzeFiles,
  generatePptx, generateWbs, getActiveAiSetting,
  type AiSetting,
} from "../api/client";
import ConfidenceBar from "../components/ConfidenceBar";
import { useToast } from "../ui/toast/ToastProvider";

type Provider = "OPENAI" | "GEMINI" | "ANTHROPIC";

const PROVIDERS: { id: Provider; label: string; defaultModel: string }[] = [
  { id: "OPENAI", label: "ChatGPT", defaultModel: "gpt-4o-mini" },
  { id: "GEMINI", label: "Google Gemini", defaultModel: "gemini-2.5-flash" },
  { id: "ANTHROPIC", label: "Claude", defaultModel: "claude-sonnet-4-6" },
];

const FIELDS: { key: keyof FormState; label: string; type?: "text" | "textarea"; placeholder?: string; required?: boolean }[] = [
  { key: "companyName", label: "회사명" },
  { key: "projectName", label: "사업명", placeholder: "에코드림(ecoDream)", required: true },
  { key: "goal", label: "사업 목표", type: "textarea" },
  { key: "scope", label: "사업의 범위", type: "textarea" },
  { key: "schedule", label: "사업 추진 일정", type: "textarea" },
  { key: "organization", label: "사업수행 조직", type: "textarea" },
  { key: "staff", label: "사업수행 인력", type: "textarea" },
  { key: "costDev", label: "소요 비용 (개발)", type: "textarea", placeholder: "참고: JIRA, Confluence, JBOSS EAP/EWS …" },
  { key: "costOps", label: "소요 비용 (운영)", type: "textarea" },
  { key: "licenseInfo", label: "인지/요금제 정보(라이선스)", type: "textarea" },
  { key: "availability", label: "가용 (지원 가능시간 등)", type: "textarea" },
  { key: "budget", label: "추진 예산" },
];

type FormState = {
  companyName?: string; projectName: string;
  goal?: string; scope?: string; schedule?: string;
  organization?: string; staff?: string;
  costDev?: string; costOps?: string;
  licenseInfo?: string; availability?: string;
  budget?: string;
};

export default function Generator() {
  // ① AI 선택
  const [provider, setProvider] = useState<Provider>("GEMINI");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(PROVIDERS[1].defaultModel);
  const [status, setStatus] = useState<"idle" | "ok" | "error" | "testing">("idle");
  const [statusText, setStatusText] = useState("Not Found");
  const [activeKey, setActiveKey] = useState<AiSetting | null>(null);

  // ② 첨부
  const noticeRef = useRef<HTMLInputElement>(null);
  const refsRef = useRef<HTMLInputElement>(null);
  const [notice, setNotice] = useState<File | null>(null);
  const [references, setReferences] = useState<File[]>([]);
  const [analyzing, setAnalyzing] = useState(false);

  // ③ 폼
  const [form, setForm] = useState<FormState>({ projectName: "" });
  const [projectUuid, setProjectUuid] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<Record<string, number>>({});
  const [analysisSummary, setAnalysisSummary] = useState<string>("");

  // ④ 산출
  const [outputs, setOutputs] = useState({ pptx: true, xlsx: true });
  const [busy, setBusy] = useState<"" | "pptx" | "xlsx">("");
  const toast = useToast();

  // ⑤ 카테고리
  const [categories, setCategories] = useState<{ code: string; name: string }[]>([]);
  const [selectedCats, setSelectedCats] = useState<string[]>([]);

  useEffect(() => {
    listCategories().then((items) => {
      setCategories(items);
      setSelectedCats(items.map((i) => i.code));
    }).catch(() => {});
    // 저장된 활성 키 자동 로드
    getActiveAiSetting().then((s) => {
      if (s) {
        setActiveKey(s);
        setProvider(s.provider as Provider);
        if (s.defaultModel) setModel(s.defaultModel);
        setStatus("ok");
        setStatusText(`저장된 키 사용중 (${s.alias || s.provider})`);
      }
    }).catch(() => {});
  }, []);

  const handleProvider = (p: Provider) => {
    setProvider(p);
    setModel(PROVIDERS.find((x) => x.id === p)!.defaultModel);
    setStatus("idle");
    setStatusText("Not Found");
  };

  const handleTest = async () => {
    if (!apiKey) return;
    setStatus("testing");
    try {
      const res = await llmTest({ provider, model, apiKey });
      if (res.error) throw new Error(res.error.message);
      setStatus("ok");
      setStatusText(`OK (${res.data.latencyMs}ms)`);
    } catch (e: any) {
      setStatus("error");
      setStatusText(e?.response?.data?.error?.message || e?.message || "검증 실패");
    }
  };

  const handleAnalyze = async () => {
    if (!notice && references.length === 0) {
      toast.warning("공고문 또는 관련 산출물을 1개 이상 첨부하세요");
      return;
    }
    setAnalyzing(true);
    try {
      const fd = new FormData();
      if (projectUuid) fd.append("projectUuid", projectUuid);
      if (notice) fd.append("notice", notice);
      references.forEach((r) => fd.append("references", r));
      // LLM 자격증명 (있는 경우만 전송 — 서버가 옵셔널 처리)
      if (apiKey && provider && model) {
        fd.append("provider", provider);
        fd.append("model", model);
        fd.append("apiKey", apiKey);
      }
      const data = await analyzeFiles(fd);
      setProjectUuid(data.projectUuid);
      if (data.fields) {
        setForm((f) => ({ ...f, ...data.fields }));
      }
      setConfidence(data.confidence || {});
      setAnalysisSummary(data.summary || "");
      const used = data.llm?.used;
      const tail = used ? ` · LLM ${data.llm.latencyMs}ms` : " · LLM 미사용";
      toast.success(`첨부 ${data.documents.length}건 분석 완료${tail}`);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || e?.message || "분석 실패");
    } finally {
      setAnalyzing(false);
    }
  };

  const ensureProject = async (): Promise<string | null> => {
    if (projectUuid) return projectUuid;
    if (!form.projectName) {
      toast.warning("사업명을 입력하세요");
      return null;
    }
    try {
      const res = await createProject({
        ...form,
        aiProvider: provider,
        aiModel: model,
      });
      setProjectUuid(res.uuid);
      toast.success(`사업 생성: ${res.uuid.slice(0, 8)}`);
      return res.uuid;
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "사업 생성 실패");
      return null;
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  const handleGenPptx = async () => {
    const uuid = await ensureProject();
    if (!uuid) return;
    setBusy("pptx");
    try {
      const llm = apiKey && provider && model ? { provider, model, apiKey } : undefined;
      const r = await generatePptx(uuid, selectedCats, llm);
      downloadBlob(r.data, `proposal-${uuid.slice(0, 8)}.pptx`);
      const usedLlm = r.headers["x-llm-used"] === "1";
      toast.success(`PPTX 생성 완료${usedLlm ? " · LLM 사용" : " · placeholder"}`);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "PPTX 생성 실패");
    } finally { setBusy(""); }
  };

  const handleGenWbs = async () => {
    const uuid = await ensureProject();
    if (!uuid) return;
    setBusy("xlsx");
    try {
      const r = await generateWbs(uuid, 5);
      downloadBlob(r.data, `wbs-${uuid.slice(0, 8)}.xlsx`);
      toast.success("WBS 생성 완료");
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "WBS 생성 실패");
    } finally { setBusy(""); }
  };

  const toggleCat = (code: string) =>
    setSelectedCats((cur) => cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]);

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">AI 사업제안서 자동 생성기</h1>
        <p className="text-sm text-white/50 mt-1">
          AI를 활용해서 사업공고나 사업 데이터를 입력하면 PPTX와 WBS를 자동 생성합니다
          {projectUuid && <span className="ml-2 text-primary"> · UUID {projectUuid.slice(0, 8)}</span>}
        </p>
      </div>

      {/* ① AI 서비스 선택 */}
      <section className="card">
        <h2 className="section-title"><Bot size={16} className="text-primary" /> AI 서비스 선택</h2>
        {activeKey ? (
          <div className="text-xs text-accent bg-accent/10 border border-accent/30 rounded-md px-3 py-2 mb-3 flex items-center gap-2">
            <KeyRound size={12} />
            저장된 활성 키 사용:
            <span className="font-semibold">{activeKey.provider}</span>
            <span className="text-white/60">{activeKey.alias ? `· ${activeKey.alias}` : ""}</span>
            <span className="font-mono text-white/40">{activeKey.keyPreview}</span>
            <Link to="/settings/ai" className="ml-auto text-white/60 hover:text-accent">관리 →</Link>
          </div>
        ) : (
          <div className="text-xs text-white/50 bg-surface/40 border border-white/10 rounded-md px-3 py-2 mb-3 flex items-center gap-2">
            <KeyRound size={12} />
            저장된 키 없음 — 아래에 직접 입력하거나
            <Link to="/settings/ai" className="text-primary hover:underline">/settings/ai 에서 등록</Link>
          </div>
        )}
        <div className="grid grid-cols-3 gap-3">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              onClick={() => handleProvider(p.id)}
              className={clsx(
                "rounded-lg border p-3 text-left transition",
                provider === p.id
                  ? "border-primary bg-primary/10"
                  : "border-white/10 hover:border-white/30"
              )}
            >
              <div className="text-sm font-semibold">{p.label}</div>
              <div className="text-xs text-white/40 mt-1">{p.defaultModel}</div>
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div>
            <label className="label">API Key</label>
            <input type="password" className="input" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="••••••••••" />
          </div>
          <div>
            <label className="label">모델</label>
            <input className="input" value={model} onChange={(e) => setModel(e.target.value)} />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-3">
          <button className="btn-primary" onClick={handleTest} disabled={!apiKey || status === "testing"}>
            {status === "testing" ? <Loader2 size={14} className="animate-spin mr-1" /> : null}
            연결 테스트
          </button>
          <span
            className={clsx(
              "ml-auto inline-flex items-center gap-1 text-xs px-2 py-1 rounded",
              status === "ok" && "bg-accent/15 text-accent",
              status === "error" && "bg-danger/15 text-danger",
              (status === "idle" || status === "testing") && "bg-white/5 text-white/60"
            )}
          >
            {status === "ok" ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />} {statusText}
          </span>
        </div>
      </section>

      {/* ② 데이터 파일 분석 */}
      <section className="card">
        <h2 className="section-title"><Upload size={16} className="text-primary" /> 데이터 파일(MD) 분석</h2>
        <div className="grid grid-cols-2 gap-3">
          <FileSlot label="사업공고(공고문)" file={notice} onPick={() => noticeRef.current?.click()} onClear={() => setNotice(null)} />
          <FileSlot
            label={`관련 산출물 (${references.length})`}
            file={references[0] || null}
            onPick={() => refsRef.current?.click()}
            onClear={() => setReferences([])}
          />
          <input ref={noticeRef} type="file" hidden accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setNotice(e.target.files?.[0] || null)} />
          <input ref={refsRef} type="file" hidden multiple accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setReferences(Array.from(e.target.files || []))} />
        </div>
        <button className="btn-ghost mt-3" onClick={handleAnalyze} disabled={analyzing}>
          {analyzing ? <Loader2 size={14} className="animate-spin mr-1" /> : <Sparkles size={14} className="mr-1" />}
          분석 시작
        </button>
      </section>

      {/* ③ 사업 정보 */}
      <section className="card">
        <h2 className="section-title">
          사업 정보 입력
          {Object.keys(confidence).length > 0 && (
            <span className="ml-2 text-[11px] font-normal text-accent bg-accent/10 px-2 py-0.5 rounded">
              <Sparkles size={10} className="inline mr-1" />LLM 자동 채움
            </span>
          )}
        </h2>

        {analysisSummary && (
          <div className="mb-4 bg-bg/60 border border-white/5 rounded-md p-3">
            <div className="text-[11px] font-semibold text-white/40 mb-1">공고문 분석 요약</div>
            <div className="text-sm text-white/80 whitespace-pre-line">{analysisSummary}</div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {FIELDS.map((f) => {
            const conf = confidence[f.key as string];
            return (
              <div key={f.key} className={clsx(f.type === "textarea" && "col-span-2")}>
                <div className="flex items-center justify-between mb-1">
                  <label className="label !mb-0">
                    {f.label}{f.required && <span className="text-danger ml-1">*</span>}
                  </label>
                  {conf != null && (
                    <div className="w-24"><ConfidenceBar value={conf} /></div>
                  )}
                </div>
                {f.type === "textarea" ? (
                  <textarea
                    className="input min-h-[72px]"
                    placeholder={f.placeholder}
                    value={(form as any)[f.key] || ""}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  />
                ) : (
                  <input
                    className="input"
                    placeholder={f.placeholder}
                    value={(form as any)[f.key] || ""}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  />
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ④ 산출 사항 */}
      <section className="card">
        <h2 className="section-title">산출 사항 업로드</h2>
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={outputs.pptx} onChange={(e) => setOutputs({ ...outputs, pptx: e.target.checked })} />
            <FileText size={14} /> 사업제안서 (PPTX)
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={outputs.xlsx} onChange={(e) => setOutputs({ ...outputs, xlsx: e.target.checked })} />
            <FileSpreadsheet size={14} /> WBS (Excel)
          </label>
        </div>
        <div className="flex gap-3 mt-4">
          <button className="btn-primary" disabled={!outputs.pptx || !!busy} onClick={handleGenPptx}>
            {busy === "pptx" ? <><Loader2 size={14} className="animate-spin mr-1" /> 생성 중...</> : "사업제안서 PPTX 생성"}
          </button>
          <button className="btn-accent" disabled={!outputs.xlsx || !!busy} onClick={handleGenWbs}>
            {busy === "xlsx" ? <><Loader2 size={14} className="animate-spin mr-1" /> 생성 중...</> : "WBS 엑셀 생성"}
          </button>
        </div>
      </section>

      {/* ⑤ 카테고리 */}
      <section className="card">
        <h2 className="section-title">사업제안서 항목 카테고리 ({selectedCats.length}/{categories.length})</h2>
        <div className="grid grid-cols-4 gap-3">
          {categories.map((c) => {
            const on = selectedCats.includes(c.code);
            return (
              <button
                key={c.code}
                onClick={() => toggleCat(c.code)}
                className={clsx(
                  "rounded-md border px-3 py-3 text-sm text-left transition",
                  on ? "border-primary bg-primary/10" : "border-white/10 hover:border-white/30"
                )}
              >
                <div className="text-xs text-white/40">{c.code}</div>
                <div>{c.name}</div>
              </button>
            );
          })}
        </div>
      </section>

    </div>
  );
}

function FileSlot({ label, file, onPick, onClear }: { label: string; file: File | null; onPick: () => void; onClear: () => void }) {
  return (
    <div
      onClick={onPick}
      className="border border-dashed border-white/15 rounded-lg p-6 text-center hover:border-primary/50 transition cursor-pointer"
    >
      <Upload className="mx-auto text-white/40" size={20} />
      <div className="text-sm mt-2">{label}</div>
      <div className="text-[11px] text-white/40 mt-1">PDF / DOCX / TXT / MD · ≤10MB</div>
      {file && (
        <div className="mt-2 inline-flex items-center gap-2 text-xs text-accent bg-accent/10 px-2 py-1 rounded">
          {file.name}
          <span
            className="text-white/40 hover:text-danger"
            onClick={(e) => { e.stopPropagation(); onClear(); }}
          >
            ✕
          </span>
        </div>
      )}
    </div>
  );
}
