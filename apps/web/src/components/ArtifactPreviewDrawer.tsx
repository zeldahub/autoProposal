import { useEffect, useMemo, useState } from "react";
import { X, Loader2, FileText, FileSpreadsheet, StickyNote, Download, Pencil, Save } from "lucide-react";
import clsx from "clsx";
import {
  getArtifactPreview, downloadArtifact, editArtifact,
  type ArtifactPreview, type PptxSlide, type XlsxSheet,
  type PptxSlideEditIn, type XlsxCellEditIn,
} from "../api/client";
import { downloadBlob, formatBytes, formatDate } from "../lib/format";
import { toastBus } from "../ui/toast/bus";

export default function ArtifactPreviewDrawer({
  artifactId, onClose, onSaved,
}: {
  artifactId: number | null;
  onClose: () => void;
  onSaved?: (newArtifactId: number) => void;
}) {
  const [data, setData] = useState<ArtifactPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [pptxDraft, setPptxDraft] = useState<PptxSlide[] | null>(null);
  const [xlsxDraft, setXlsxDraft] = useState<XlsxSheet[] | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!artifactId) return;
    setData(null); setError(null); setLoading(true); setEditMode(false);
    setPptxDraft(null); setXlsxDraft(null);
    getArtifactPreview(artifactId)
      .then((d) => {
        setData(d);
        if (d.format === "PPTX") setPptxDraft(JSON.parse(JSON.stringify(d.slides)));
        if (d.format === "XLSX") setXlsxDraft(JSON.parse(JSON.stringify(d.sheets)));
      })
      .catch((e) => setError(e?.response?.data?.error?.message || "미리보기 실패"))
      .finally(() => setLoading(false));
  }, [artifactId]);

  if (!artifactId) return null;

  const Icon = data?.type === "PPTX" ? FileText : FileSpreadsheet;

  const handleDownload = async () => {
    if (!data) return;
    const r = await downloadArtifact(data.id);
    downloadBlob(r.data, data.filename);
  };

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    try {
      let result;
      if (data.format === "PPTX" && pptxDraft) {
        const orig = data.slides;
        const edits: PptxSlideEditIn[] = [];
        pptxDraft.forEach((s, i) => {
          const o = orig[i];
          if (!o) return;
          const titleChanged = s.title !== o.title;
          const bulletsChanged = JSON.stringify(s.bullets) !== JSON.stringify(o.bullets);
          const noteChanged = s.speakerNote !== o.speakerNote;
          if (titleChanged || bulletsChanged || noteChanged) {
            edits.push({
              index: s.index,
              title: titleChanged ? s.title : null,
              bullets: bulletsChanged ? s.bullets : null,
              speakerNote: noteChanged ? s.speakerNote : null,
            });
          }
        });
        if (!edits.length) {
          toastBus.warning("변경사항이 없습니다.");
          setSaving(false);
          return;
        }
        result = await editArtifact(data.id, { pptxEdits: edits });
      } else if (data.format === "XLSX" && xlsxDraft) {
        const orig = data.sheets;
        const edits: XlsxCellEditIn[] = [];
        xlsxDraft.forEach((sh, si) => {
          const o = orig[si];
          if (!o) return;
          sh.rows.forEach((row, ri) => {
            const orow = o.rows[ri] || [];
            row.forEach((cell, ci) => {
              if (cell !== (orow[ci] ?? "")) {
                edits.push({ sheet: sh.name, row: ri + 1, col: ci + 1, value: cell });
              }
            });
          });
        });
        if (!edits.length) {
          toastBus.warning("변경사항이 없습니다.");
          setSaving(false);
          return;
        }
        result = await editArtifact(data.id, { xlsxEdits: edits });
      } else {
        return;
      }
      toastBus.success(`v${result.version} 으로 저장되었습니다.`);
      setEditMode(false);
      onSaved?.(result.id);
      // 새 버전을 자동으로 열어 표시
      const fresh = await getArtifactPreview(result.id);
      setData(fresh);
      if (fresh.format === "PPTX") setPptxDraft(JSON.parse(JSON.stringify(fresh.slides)));
      if (fresh.format === "XLSX") setXlsxDraft(JSON.parse(JSON.stringify(fresh.sheets)));
    } catch (e: any) {
      toastBus.error(e?.response?.data?.error?.message || "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div className="flex-1 bg-black/60 backdrop-blur-sm" />
      <aside
        className="w-[860px] max-w-[95vw] bg-surface border-l border-white/10 shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="px-5 py-4 border-b border-white/5 flex items-center gap-3">
          <Icon size={18} className="text-primary" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold truncate">{data?.filename || "로딩 중..."}</div>
            {data && (
              <div className="text-[11px] text-white/40 mt-0.5">
                {data.type} v{data.version} · {formatBytes(data.sizeBytes)} · {formatDate(data.createdAt)}
                {data.format === "PPTX" && ` · ${data.totalSlides}슬라이드`}
                {data.format === "XLSX" && ` · ${data.totalSheets}시트`}
                {editMode && <span className="ml-2 text-primary">· 편집 모드</span>}
              </div>
            )}
          </div>
          {data && !editMode && (
            <>
              <button className="btn-ghost" onClick={() => setEditMode(true)} title="인라인 편집">
                <Pencil size={14} className="mr-1" />편집
              </button>
              <button className="btn-ghost" onClick={handleDownload} title="원본 다운로드">
                <Download size={14} className="mr-1" />다운로드
              </button>
            </>
          )}
          {data && editMode && (
            <>
              <button
                className="btn-ghost text-white/60"
                onClick={() => {
                  setEditMode(false);
                  if (data.format === "PPTX") setPptxDraft(JSON.parse(JSON.stringify(data.slides)));
                  if (data.format === "XLSX") setXlsxDraft(JSON.parse(JSON.stringify(data.sheets)));
                }}
                disabled={saving}
              >
                취소
              </button>
              <button className="btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : <Save size={14} className="mr-1" />}
                새 버전 저장
              </button>
            </>
          )}
          <button className="p-2 hover:bg-white/5 rounded" onClick={onClose} aria-label="닫기">
            <X size={16} />
          </button>
        </header>

        {loading && (
          <div className="flex-1 flex items-center justify-center text-white/50">
            <Loader2 className="animate-spin mr-2" size={16} /> 미리보기 로딩 중...
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center text-danger">{error}</div>
        )}

        {data && !loading && data.format === "PPTX" && (
          editMode && pptxDraft ? (
            <PptxEditView slides={pptxDraft} onChange={setPptxDraft} />
          ) : (
            <PptxView slides={data.slides} totalSlides={data.totalSlides} shownSlides={data.shownSlides} />
          )
        )}

        {data && !loading && data.format === "XLSX" && (
          editMode && xlsxDraft ? (
            <XlsxEditView sheets={xlsxDraft} onChange={setXlsxDraft} />
          ) : (
            <XlsxView sheets={data.sheets} />
          )
        )}
      </aside>
    </div>
  );
}

function PptxView({ slides, totalSlides, shownSlides }: { slides: PptxSlide[]; totalSlides: number; shownSlides: number }) {
  return (
    <div className="flex-1 overflow-y-auto px-5 py-4">
      {totalSlides > shownSlides && (
        <div className="text-[11px] text-white/40 mb-3">
          전체 {totalSlides}개 중 {shownSlides}개 표시
        </div>
      )}
      <div className="space-y-3">
        {slides.map((s) => (
          <SlideCard key={s.index} slide={s} />
        ))}
      </div>
    </div>
  );
}

function SlideCard({ slide }: { slide: PptxSlide }) {
  return (
    <div className="bg-bg/60 border border-white/5 rounded-md overflow-hidden">
      <div className="px-4 py-3 border-b border-white/5 flex items-baseline gap-3 bg-white/[0.02]">
        <span className="text-[10px] font-mono text-white/40 w-8 shrink-0">#{slide.index}</span>
        <h3 className="font-semibold text-white/90 break-words">{slide.title || "(제목 없음)"}</h3>
      </div>
      <div className="px-4 py-3">
        {slide.bullets.length === 0 ? (
          <div className="text-xs text-white/30 italic">(본문 없음)</div>
        ) : (
          <ul className="space-y-1.5 text-sm text-white/80">
            {slide.bullets.map((b, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-primary/60 shrink-0">•</span>
                <span className="break-words">{b}</span>
              </li>
            ))}
          </ul>
        )}
        {slide.speakerNote && (
          <div className="mt-3 pt-3 border-t border-white/5 flex gap-2 text-xs text-white/50">
            <StickyNote size={12} className="mt-0.5 shrink-0 text-yellow-500/70" />
            <span className="whitespace-pre-line">{slide.speakerNote}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function PptxEditView({ slides, onChange }: { slides: PptxSlide[]; onChange: (next: PptxSlide[]) => void }) {
  const update = (idx: number, patch: Partial<PptxSlide>) => {
    onChange(slides.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  };
  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
      {slides.map((s, i) => (
        <div key={s.index} className="bg-bg/60 border border-white/5 rounded-md p-4 space-y-3">
          <div className="flex items-baseline gap-3">
            <span className="text-[10px] font-mono text-white/40 w-8 shrink-0">#{s.index}</span>
            <input
              className="input flex-1 font-semibold"
              value={s.title}
              onChange={(e) => update(i, { title: e.target.value })}
              placeholder="제목"
            />
          </div>
          <div>
            <label className="text-[11px] text-white/50 mb-1 block">본문 (한 줄당 1 bullet)</label>
            <textarea
              className="input w-full min-h-[100px] text-sm"
              value={s.bullets.join("\n")}
              onChange={(e) =>
                update(i, { bullets: e.target.value.split(/\r?\n/).filter((l) => l.trim() !== "") })
              }
              placeholder="첫 번째 bullet&#10;두 번째 bullet"
            />
          </div>
          <div>
            <label className="text-[11px] text-white/50 mb-1 block flex items-center gap-1">
              <StickyNote size={11} className="text-yellow-500/70" /> 발표자 노트
            </label>
            <textarea
              className="input w-full min-h-[60px] text-xs"
              value={s.speakerNote}
              onChange={(e) => update(i, { speakerNote: e.target.value })}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function XlsxView({ sheets }: { sheets: XlsxSheet[] }) {
  const [active, setActive] = useState(0);
  if (sheets.length === 0) {
    return <div className="flex-1 flex items-center justify-center text-white/40">시트 없음</div>;
  }
  const cur = sheets[active];
  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="px-5 pt-3 border-b border-white/5 flex gap-1 overflow-x-auto">
        {sheets.map((s, i) => (
          <button
            key={s.name}
            onClick={() => setActive(i)}
            className={clsx(
              "px-3 py-2 text-xs whitespace-nowrap border-b-2 -mb-px transition",
              active === i ? "border-primary text-primary" : "border-transparent text-white/60 hover:text-white/80"
            )}
          >
            {s.name}
            <span className="ml-1 text-[10px] text-white/30">({s.totalRows}×{s.totalCols})</span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto">
        {cur.rows.length === 0 ? (
          <div className="text-center text-white/40 py-12">빈 시트</div>
        ) : (
          <table className="w-full text-xs border-collapse">
            <tbody>
              {cur.rows.map((row, ri) => (
                <tr key={ri} className={ri === 0 ? "bg-primary/10" : "hover:bg-white/[0.02]"}>
                  <td className="sticky left-0 bg-surface px-2 py-1.5 text-right text-[10px] text-white/30 border border-white/5 font-mono">
                    {ri + 1}
                  </td>
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className={clsx(
                        "px-2 py-1.5 border border-white/5 align-top max-w-[240px] truncate",
                        ri === 0 && "font-semibold text-white/90"
                      )}
                      title={cell.length > 40 ? cell : undefined}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {cur.totalRows > cur.shownRows && (
          <div className="text-[11px] text-white/40 px-3 py-2 border-t border-white/5 sticky bottom-0 bg-surface">
            전체 {cur.totalRows}행 중 {cur.shownRows}행 표시 — 전체 보기는 다운로드 후 확인
          </div>
        )}
      </div>
    </div>
  );
}

function XlsxEditView({ sheets, onChange }: { sheets: XlsxSheet[]; onChange: (next: XlsxSheet[]) => void }) {
  const [active, setActive] = useState(0);
  if (sheets.length === 0) {
    return <div className="flex-1 flex items-center justify-center text-white/40">시트 없음</div>;
  }
  const cur = sheets[active];
  const setCell = (ri: number, ci: number, val: string) => {
    const next = sheets.map((s, si) => {
      if (si !== active) return s;
      const rows = s.rows.map((row, rri) =>
        rri === ri ? row.map((c, cci) => (cci === ci ? val : c)) : row,
      );
      return { ...s, rows };
    });
    onChange(next);
  };
  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="px-5 pt-3 border-b border-white/5 flex gap-1 overflow-x-auto">
        {sheets.map((s, i) => (
          <button
            key={s.name}
            onClick={() => setActive(i)}
            className={clsx(
              "px-3 py-2 text-xs whitespace-nowrap border-b-2 -mb-px transition",
              active === i ? "border-primary text-primary" : "border-transparent text-white/60 hover:text-white/80"
            )}
          >
            {s.name}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {cur.rows.length === 0 ? (
          <div className="text-center text-white/40 py-12">빈 시트</div>
        ) : (
          <table className="w-full text-xs border-collapse">
            <tbody>
              {cur.rows.map((row, ri) => (
                <tr key={ri}>
                  <td className="sticky left-0 bg-surface px-2 py-1 text-right text-[10px] text-white/30 border border-white/5 font-mono">
                    {ri + 1}
                  </td>
                  {row.map((cell, ci) => (
                    <td key={ci} className="border border-white/5 p-0">
                      <input
                        className="w-full bg-transparent px-2 py-1 text-xs focus:bg-primary/10 outline-none"
                        value={cell}
                        onChange={(e) => setCell(ri, ci, e.target.value)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="text-[11px] text-white/40 px-3 py-2 border-t border-white/5 bg-surface">
        편집은 미리보기 범위(최대 {cur.shownRows}행) 내에서만 적용됩니다. 그 외 셀은 보존됩니다.
      </div>
    </div>
  );
}
