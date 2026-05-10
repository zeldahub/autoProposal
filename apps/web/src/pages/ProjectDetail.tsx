import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Download, Trash2, FileText, FileSpreadsheet,
  RefreshCw, Loader2, Edit3, Save, X, Eye, Sparkles, FileSearch,
  Maximize2, Copy, Archive,
} from "lucide-react";
import {
  getProject, updateProject, deleteProject,
  listProjectArtifacts, listProjectLlmLogs,
  listProjectAttachments, getProjectAnalysis,
  downloadArtifact, deleteArtifact, exportProjectZip,
  type ProjectDetail as Detail, type ArtifactItem, type LlmLogItem, type ProjectIn,
  type AttachmentItem, type ProjectAnalysis,
} from "../api/client";
import { downloadBlob, formatBytes, formatDate, shortUuid } from "../lib/format";
import StatusBadge from "../components/StatusBadge";
import ConfidenceBar from "../components/ConfidenceBar";
import PreviewDrawer from "../components/PreviewDrawer";
import ArtifactPreviewDrawer from "../components/ArtifactPreviewDrawer";
import CloneProjectModal from "../components/CloneProjectModal";
import CollabPanel from "../components/CollabPanel";
import { useConfirm } from "../ui/confirm/ConfirmProvider";
import { useToast } from "../ui/toast/ToastProvider";

const FIELD_GROUPS: { label: string; key: keyof Detail; multi?: boolean }[] = [
  { label: "회사명", key: "companyName" },
  { label: "사업명", key: "projectName" },
  { label: "사업 목표", key: "goal", multi: true },
  { label: "사업의 범위", key: "scope", multi: true },
  { label: "사업 추진 일정", key: "schedule", multi: true },
  { label: "사업수행 조직", key: "organization", multi: true },
  { label: "사업수행 인력", key: "staff", multi: true },
  { label: "소요 비용 (개발)", key: "costDev", multi: true },
  { label: "소요 비용 (운영)", key: "costOps", multi: true },
  { label: "라이선스", key: "licenseInfo", multi: true },
  { label: "가용성", key: "availability", multi: true },
  { label: "추진 예산", key: "budget" },
];

export default function ProjectDetail() {
  const { uuid = "" } = useParams();
  const nav = useNavigate();
  const [project, setProject] = useState<Detail | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [logs, setLogs] = useState<LlmLogItem[]>([]);
  const [attachments, setAttachments] = useState<AttachmentItem[]>([]);
  const [analysis, setAnalysis] = useState<ProjectAnalysis | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [artifactPreviewId, setArtifactPreviewId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [edit, setEdit] = useState<Partial<Detail>>({});
  const [tab, setTab] = useState<"analysis" | "artifacts" | "logs" | "collab">("analysis");
  const [cloneOpen, setCloneOpen] = useState(false);
  const confirm = useConfirm();
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const [p, a, l, att, ana] = await Promise.all([
        getProject(uuid),
        listProjectArtifacts(uuid),
        listProjectLlmLogs(uuid),
        listProjectAttachments(uuid),
        getProjectAnalysis(uuid),
      ]);
      setProject(p);
      setArtifacts(a);
      setLogs(l);
      setAttachments(att);
      setAnalysis(ana);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [uuid]);

  const beginEdit = () => {
    if (!project) return;
    setEdit({ ...project });
    setEditing(true);
  };

  const cancelEdit = () => {
    setEdit({});
    setEditing(false);
  };

  const save = async () => {
    if (!project) return;
    setSaving(true);
    try {
      const body: ProjectIn = {
        companyName: edit.companyName || undefined,
        projectName: edit.projectName || project.projectName,
        goal: edit.goal || undefined,
        scope: edit.scope || undefined,
        schedule: edit.schedule || undefined,
        organization: edit.organization || undefined,
        staff: edit.staff || undefined,
        costDev: edit.costDev || undefined,
        costOps: edit.costOps || undefined,
        licenseInfo: edit.licenseInfo || undefined,
        availability: edit.availability || undefined,
        budget: edit.budget || undefined,
        aiProvider: edit.aiProvider || undefined,
        aiModel: edit.aiModel || undefined,
      };
      const updated = await updateProject(uuid, body);
      setProject(updated);
      setEditing(false);
      toast.success("사업 정보가 저장되었습니다.");
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "저장 실패");
    } finally { setSaving(false); }
  };

  const handleDownload = async (a: ArtifactItem) => {
    const r = await downloadArtifact(a.id);
    downloadBlob(r.data, a.filename);
  };

  const handleDeleteArtifact = async (a: ArtifactItem) => {
    const ok = await confirm({
      title: "산출물 삭제",
      message: `${a.type} v${a.version} 을 삭제하시겠습니까?`,
      description: `파일: ${a.filename}`,
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    await deleteArtifact(a.id);
    toast.success("산출물이 삭제되었습니다.");
    await load();
  };

  const handleDeleteProject = async () => {
    const ok = await confirm({
      title: "사업 삭제",
      message: `'${project?.projectName || ""}' 사업을 휴지통으로 이동합니다.`,
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    await deleteProject(uuid);
    toast.success("사업이 삭제되었습니다.");
    nav("/projects", { replace: true });
  };

  if (loading) {
    return <div className="flex items-center gap-2 text-white/50"><Loader2 className="animate-spin" size={16} /> 로딩 중...</div>;
  }
  if (!project) {
    return <div className="text-white/50">사업을 찾을 수 없습니다.</div>;
  }

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center gap-3">
        <Link to="/projects" className="text-white/50 hover:text-white"><ArrowLeft size={18} /></Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{project.projectName}</h1>
            <StatusBadge status={project.status} />
          </div>
          <div className="text-xs text-white/40 mt-0.5">
            {project.companyName || "회사명 없음"} · UUID {shortUuid(project.uuid)} · 수정 {formatDate(project.updatedAt)}
          </div>
        </div>
        {!editing && (
          <>
            <button className="btn-ghost" onClick={() => setCloneOpen(true)}>
              <Copy size={14} className="mr-1" />복제
            </button>
            <button className="btn-ghost" onClick={async () => {
              try {
                const r = await exportProjectZip(project.uuid);
                downloadBlob(r.data, `lon-${project.projectName.replace(/\s+/g,'_')}.zip`);
                toast.success("백업이 다운로드되었습니다.");
              } catch (e: any) {
                toast.error(e?.response?.data?.error?.message || "백업 실패");
              }
            }}>
              <Archive size={14} className="mr-1" />백업
            </button>
            <button className="btn-ghost" onClick={beginEdit}><Edit3 size={14} className="mr-1" />편집</button>
            <button className="btn-ghost text-danger" onClick={handleDeleteProject}>
              <Trash2 size={14} className="mr-1" />삭제
            </button>
          </>
        )}
        {editing && (
          <>
            <button className="btn-ghost" onClick={cancelEdit} disabled={saving}><X size={14} className="mr-1" />취소</button>
            <button className="btn-primary" onClick={save} disabled={saving}>
              {saving ? <Loader2 className="animate-spin mr-1" size={14} /> : <Save size={14} className="mr-1" />}
              저장
            </button>
          </>
        )}
      </div>

      {/* 사업 정보 */}
      <section className="card">
        <h2 className="section-title">사업 정보</h2>
        <div className="grid grid-cols-2 gap-3">
          {FIELD_GROUPS.map((f) => (
            <div key={f.key} className={f.multi ? "col-span-2" : ""}>
              <label className="label">{f.label}</label>
              {!editing ? (
                <div className={`text-sm ${(project[f.key] ? "text-white" : "text-white/30")} whitespace-pre-line`}>
                  {(project[f.key] as string) || "-"}
                </div>
              ) : f.multi ? (
                <textarea
                  className="input min-h-[72px]"
                  value={(edit[f.key] as string) || ""}
                  onChange={(e) => setEdit({ ...edit, [f.key]: e.target.value })}
                />
              ) : (
                <input
                  className="input"
                  value={(edit[f.key] as string) || ""}
                  onChange={(e) => setEdit({ ...edit, [f.key]: e.target.value })}
                />
              )}
            </div>
          ))}
          <div>
            <label className="label">AI Provider</label>
            <div className="text-sm text-white/70">{project.aiProvider || "-"}</div>
          </div>
          <div>
            <label className="label">AI Model</label>
            <div className="text-sm text-white/70">{project.aiModel || "-"}</div>
          </div>
        </div>
      </section>

      {/* 탭 */}
      <section className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex gap-1 p-1 bg-bg rounded-md">
            <button
              onClick={() => setTab("analysis")}
              className={`px-3 py-1.5 text-sm rounded ${tab === "analysis" ? "bg-primary text-white" : "text-white/60"}`}
            ><Sparkles size={12} className="inline mr-1" />분석 ({attachments.length})</button>
            <button
              onClick={() => setTab("artifacts")}
              className={`px-3 py-1.5 text-sm rounded ${tab === "artifacts" ? "bg-primary text-white" : "text-white/60"}`}
            >산출물 ({artifacts.length})</button>
            <button
              onClick={() => setTab("logs")}
              className={`px-3 py-1.5 text-sm rounded ${tab === "logs" ? "bg-primary text-white" : "text-white/60"}`}
            >LLM 호출 이력 ({logs.length})</button>
            <button
              onClick={() => setTab("collab")}
              className={`px-3 py-1.5 text-sm rounded ${tab === "collab" ? "bg-primary text-white" : "text-white/60"}`}
            >협업</button>
          </div>
          <button className="btn-ghost" onClick={load}><RefreshCw size={14} className="mr-1" />새로고침</button>
        </div>

        {tab === "analysis" && <AnalysisTab attachments={attachments} analysis={analysis} onPreview={setPreviewId} />}
        {tab === "artifacts" && (
          <ArtifactTable
            items={artifacts}
            onDownload={handleDownload}
            onDelete={handleDeleteArtifact}
            onPreview={setArtifactPreviewId}
          />
        )}
        {tab === "logs" && <LogTable items={logs} />}
        {tab === "collab" && <CollabPanel projectUuid={project.uuid} isOwner={true} />}
      </section>

      <PreviewDrawer mongoDocId={previewId} onClose={() => setPreviewId(null)} />
      <ArtifactPreviewDrawer artifactId={artifactPreviewId} onClose={() => setArtifactPreviewId(null)} />
      <CloneProjectModal
        open={cloneOpen}
        onClose={() => setCloneOpen(false)}
        sourceUuid={project.uuid}
        sourceName={project.projectName}
        attachmentCount={attachments.length}
        onCloned={(newUuid) => {
          setCloneOpen(false);
          nav(`/projects/${newUuid}`);
        }}
      />
    </div>
  );
}

const ANALYSIS_LABELS: { key: string; label: string }[] = [
  { key: "companyName", label: "회사명" },
  { key: "projectName", label: "사업명" },
  { key: "goal", label: "사업 목표" },
  { key: "scope", label: "사업의 범위" },
  { key: "schedule", label: "사업 추진 일정" },
  { key: "organization", label: "사업수행 조직" },
  { key: "staff", label: "사업수행 인력" },
  { key: "costDev", label: "소요 비용 (개발)" },
  { key: "costOps", label: "소요 비용 (운영)" },
  { key: "licenseInfo", label: "라이선스" },
  { key: "availability", label: "가용성" },
  { key: "budget", label: "추진 예산" },
];

function AnalysisTab({
  attachments, analysis, onPreview,
}: {
  attachments: AttachmentItem[];
  analysis: ProjectAnalysis | null;
  onPreview: (id: string) => void;
}) {
  return (
    <div className="space-y-5">
      {/* 첨부 */}
      <div>
        <h3 className="text-xs font-semibold text-white/50 mb-2 flex items-center gap-1">
          <FileSearch size={12} /> 첨부 파일 ({attachments.length})
        </h3>
        {attachments.length === 0 ? (
          <div className="text-sm text-white/40 text-center py-4 border border-dashed border-white/10 rounded">
            첨부된 파일이 없습니다.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {attachments.map((a) => (
              <button
                key={a.id}
                onClick={() => a.mongoDocId && onPreview(a.mongoDocId)}
                disabled={!a.mongoDocId}
                className="text-left bg-bg/50 border border-white/10 rounded-md px-3 py-2.5 hover:border-primary/40 transition group disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${a.slot === "NOTICE" ? "bg-primary/15 text-primary" : "bg-white/5 text-white/60"}`}>
                    {a.slot}
                  </span>
                  <span className="text-sm font-mono truncate flex-1">{a.filename}</span>
                  <Eye size={14} className="text-white/30 group-hover:text-primary" />
                </div>
                <div className="text-[11px] text-white/40 mt-1 ml-1">
                  {formatBytes(a.sizeBytes)} · {formatDate(a.createdAt)}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 분석 결과 */}
      <div>
        <h3 className="text-xs font-semibold text-white/50 mb-2 flex items-center gap-1">
          <Sparkles size={12} /> LLM 분석 결과
          {analysis?.model && <span className="text-white/30">· {analysis.model}</span>}
          {analysis?.createdAt && <span className="text-white/30">· {formatDate(analysis.createdAt)}</span>}
        </h3>
        {!analysis ? (
          <div className="text-sm text-white/40 text-center py-6 border border-dashed border-white/10 rounded">
            아직 LLM 분석이 수행되지 않았습니다.
            <div className="text-[11px] text-white/30 mt-1">
              생성기에서 첨부 + AI 키로 [분석 시작] 후 다시 확인하세요.
            </div>
          </div>
        ) : (
          <>
            {analysis.summary && (
              <div className="bg-bg/60 border border-white/5 rounded p-3 mb-3 text-sm text-white/80 whitespace-pre-line">
                {analysis.summary}
              </div>
            )}
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/50 border-b border-white/5">
                  <th className="px-2 py-2 w-40">항목</th>
                  <th className="px-2 py-2">추출 값</th>
                  <th className="px-2 py-2 w-32">신뢰도</th>
                </tr>
              </thead>
              <tbody>
                {ANALYSIS_LABELS.map(({ key, label }) => {
                  const val = analysis.fields[key] || "";
                  const conf = analysis.confidence[key];
                  return (
                    <tr key={key} className="border-b border-white/5 align-top">
                      <td className="px-2 py-2 text-white/70">{label}</td>
                      <td className="px-2 py-2">
                        {val ? (
                          <span className="text-sm whitespace-pre-line">{val}</span>
                        ) : (
                          <span className="text-white/30 text-xs">(없음)</span>
                        )}
                      </td>
                      <td className="px-2 py-2"><ConfidenceBar value={conf} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}

function ArtifactTable({ items, onDownload, onDelete, onPreview }: {
  items: ArtifactItem[];
  onDownload: (a: ArtifactItem) => void;
  onDelete: (a: ArtifactItem) => void;
  onPreview: (id: number) => void;
}) {
  if (items.length === 0) return <div className="text-center text-white/40 py-8">생성된 산출물이 없습니다.</div>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-white/50 border-b border-white/5">
          <th className="px-3 py-2 w-20">유형</th>
          <th className="px-3 py-2 w-16">버전</th>
          <th className="px-3 py-2">파일명</th>
          <th className="px-3 py-2 w-24">크기</th>
          <th className="px-3 py-2 w-44">생성일</th>
          <th className="px-3 py-2 w-24"></th>
        </tr>
      </thead>
      <tbody>
        {items.map((a) => {
          const Icon = a.type === "PPTX" ? FileText : FileSpreadsheet;
          return (
            <tr key={a.id} className="border-b border-white/5 hover:bg-white/5">
              <td className="px-3 py-2"><Icon size={14} className="inline mr-1 text-primary" />{a.type}</td>
              <td className="px-3 py-2 text-white/60">v{a.version}</td>
              <td className="px-3 py-2 font-mono text-xs">{a.filename}</td>
              <td className="px-3 py-2 text-white/60">{formatBytes(a.sizeBytes)}</td>
              <td className="px-3 py-2 text-xs text-white/50">{formatDate(a.createdAt)}</td>
              <td className="px-3 py-2 text-right">
                <button className="inline-flex p-1.5 hover:bg-white/10 rounded" onClick={() => onPreview(a.id)} title="미리보기">
                  <Maximize2 size={14} />
                </button>
                <button className="inline-flex p-1.5 hover:bg-white/10 rounded ml-1" onClick={() => onDownload(a)} title="다운로드">
                  <Download size={14} />
                </button>
                <button className="inline-flex p-1.5 hover:bg-danger/20 hover:text-danger rounded ml-1" onClick={() => onDelete(a)} title="삭제">
                  <Trash2 size={14} />
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function LogTable({ items }: { items: LlmLogItem[] }) {
  if (items.length === 0) return <div className="text-center text-white/40 py-8">LLM 호출 이력이 없습니다.</div>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-white/50 border-b border-white/5">
          <th className="px-3 py-2 w-20">목적</th>
          <th className="px-3 py-2 w-24">Provider</th>
          <th className="px-3 py-2 w-40">모델</th>
          <th className="px-3 py-2 w-16">in</th>
          <th className="px-3 py-2 w-16">out</th>
          <th className="px-3 py-2 w-24">지연</th>
          <th className="px-3 py-2 w-20">상태</th>
          <th className="px-3 py-2 w-44">시각</th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.id} className="border-b border-white/5 hover:bg-white/5">
            <td className="px-3 py-2">{r.purpose}</td>
            <td className="px-3 py-2">{r.provider}</td>
            <td className="px-3 py-2 font-mono text-xs">{r.model}</td>
            <td className="px-3 py-2 text-white/60">{r.inputTokens ?? "-"}</td>
            <td className="px-3 py-2 text-white/60">{r.outputTokens ?? "-"}</td>
            <td className="px-3 py-2 text-white/60">{r.latencyMs ? `${r.latencyMs}ms` : "-"}</td>
            <td className="px-3 py-2">
              {r.errorCode ? (
                <span className="text-danger text-xs">{r.errorCode}</span>
              ) : (
                <span className="text-accent text-xs">{r.httpStatus}</span>
              )}
            </td>
            <td className="px-3 py-2 text-xs text-white/50">{formatDate(r.createdAt)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
