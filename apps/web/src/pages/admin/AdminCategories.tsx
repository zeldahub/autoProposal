import { useEffect, useState } from "react";
import { Plus, Trash2, Loader2, Save, X, Power, ListTree } from "lucide-react";
import clsx from "clsx";
import {
  adminListCategories, adminCreateCategory,
  adminUpdateCategory, adminDeleteCategory,
  type Category,
} from "../../api/client";
import { useConfirm } from "../../ui/confirm/ConfirmProvider";
import { useToast } from "../../ui/toast/ToastProvider";

export default function AdminCategories() {
  const [items, setItems] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [edit, setEdit] = useState<Partial<Category>>({});
  const [adding, setAdding] = useState(false);
  const [add, setAdd] = useState({
    code: "", nameKo: "", sortOrder: 50, isActive: true,
    slideTemplateKey: "", systemPrompt: "",
  });
  const confirm = useConfirm();
  const toast = useToast();

  const reload = async () => {
    setLoading(true);
    try { setItems(await adminListCategories(true)); }
    finally { setLoading(false); }
  };

  useEffect(() => { reload(); }, []);

  const beginEdit = (c: Category) => {
    setEdit({ ...c });
    setEditing(c.code);
  };

  const cancelEdit = () => { setEdit({}); setEditing(null); };

  const save = async () => {
    if (!editing) return;
    setBusy(editing);
    try {
      await adminUpdateCategory(editing, {
        nameKo: edit.nameKo,
        sortOrder: edit.sortOrder,
        slideTemplateKey: edit.slideTemplateKey || undefined,
        systemPrompt: edit.systemPrompt || undefined,
        isActive: edit.isActive,
      });
      cancelEdit();
      toast.success("카테고리가 수정되었습니다.");
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "저장 실패");
    } finally { setBusy(null); }
  };

  const toggle = async (c: Category) => {
    setBusy(c.code);
    try {
      await adminUpdateCategory(c.code, { isActive: !c.isActive });
      await reload();
    } finally { setBusy(null); }
  };

  const remove = async (c: Category) => {
    const ok = await confirm({
      title: "카테고리 삭제",
      message: `${c.code} (${c.nameKo})을 삭제합니다.`,
      description: "기존 사업제안서 생성에 사용된 카테고리는 삭제 후 표시되지 않습니다.",
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (!ok) return;
    setBusy(c.code);
    try {
      await adminDeleteCategory(c.code);
      toast.success("카테고리가 삭제되었습니다.");
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "삭제 실패");
    } finally { setBusy(null); }
  };

  const submitAdd = async () => {
    if (!add.code || !add.nameKo) {
      toast.warning("코드와 이름은 필수입니다.");
      return;
    }
    try {
      await adminCreateCategory({
        code: add.code.toUpperCase(),
        nameKo: add.nameKo,
        sortOrder: add.sortOrder,
        isActive: add.isActive,
        slideTemplateKey: add.slideTemplateKey || undefined,
        systemPrompt: add.systemPrompt || undefined,
      });
      setAdding(false);
      setAdd({ code: "", nameKo: "", sortOrder: 50, isActive: true, slideTemplateKey: "", systemPrompt: "" });
      toast.success("카테고리가 추가되었습니다.");
      await reload();
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || "추가 실패");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ListTree size={20} className="text-primary" /> 표준 목차 관리
        </h1>
        <span className="text-sm text-white/40">{items.length}개</span>
        <button className="btn-primary ml-auto" onClick={() => setAdding(true)} disabled={adding}>
          <Plus size={14} className="mr-1" /> 카테고리 추가
        </button>
      </div>

      <div className="text-xs text-white/50 bg-surface/40 border border-white/5 rounded-md px-4 py-3">
        활성화된 카테고리만 사용자가 사업제안서 생성 시 선택할 수 있습니다.
        <span className="text-accent ml-1">시스템 프롬프트</span>를 설정하면 LLM이 해당 카테고리 슬라이드를 만들 때 사용됩니다.
      </div>

      {adding && (
        <div className="card border-primary/40">
          <h2 className="section-title">신규 카테고리</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">코드 (대문자/숫자/_)</label>
              <input className="input font-mono" value={add.code}
                onChange={(e) => setAdd({ ...add, code: e.target.value.toUpperCase() })}
                placeholder="예: PROCUREMENT" />
            </div>
            <div>
              <label className="label">이름 (한글)</label>
              <input className="input" value={add.nameKo}
                onChange={(e) => setAdd({ ...add, nameKo: e.target.value })}
                placeholder="예: 조달 사항" />
            </div>
            <div>
              <label className="label">정렬 순서</label>
              <input type="number" className="input" value={add.sortOrder}
                onChange={(e) => setAdd({ ...add, sortOrder: Number(e.target.value) })} />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={add.isActive}
                  onChange={(e) => setAdd({ ...add, isActive: e.target.checked })} />
                활성화
              </label>
            </div>
            <div className="col-span-2">
              <label className="label">시스템 프롬프트 (선택)</label>
              <textarea className="input min-h-[60px]" value={add.systemPrompt}
                onChange={(e) => setAdd({ ...add, systemPrompt: e.target.value })}
                placeholder="LLM에 전달할 추가 지침 (없으면 기본 사용)" />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button className="btn-primary" onClick={submitAdd}>저장</button>
            <button className="btn-ghost" onClick={() => setAdding(false)}>취소</button>
          </div>
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-white/50 border-b border-white/5">
              <th className="px-4 py-3 w-32">코드</th>
              <th className="px-4 py-3 w-44">이름</th>
              <th className="px-4 py-3 w-20">순서</th>
              <th className="px-4 py-3">시스템 프롬프트</th>
              <th className="px-4 py-3 w-20">상태</th>
              <th className="px-4 py-3 w-32"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-white/40">
                <Loader2 className="inline animate-spin mr-2" size={14} /> 로딩 중...
              </td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-white/40">카테고리 없음</td></tr>
            )}
            {!loading && items.map((c) => {
              const isEdit = editing === c.code;
              return (
                <tr key={c.code} className="border-b border-white/5 align-top">
                  <td className="px-4 py-3 font-mono text-xs">{c.code}</td>
                  <td className="px-4 py-3">
                    {isEdit ? (
                      <input className="input" value={edit.nameKo || ""}
                        onChange={(e) => setEdit({ ...edit, nameKo: e.target.value })} />
                    ) : c.nameKo}
                  </td>
                  <td className="px-4 py-3">
                    {isEdit ? (
                      <input type="number" className="input w-20" value={edit.sortOrder ?? 50}
                        onChange={(e) => setEdit({ ...edit, sortOrder: Number(e.target.value) })} />
                    ) : <span className="text-white/60">{c.sortOrder}</span>}
                  </td>
                  <td className="px-4 py-3">
                    {isEdit ? (
                      <textarea className="input min-h-[48px]" value={edit.systemPrompt || ""}
                        onChange={(e) => setEdit({ ...edit, systemPrompt: e.target.value })} />
                    ) : (
                      <span className="text-white/50 text-xs line-clamp-2">{c.systemPrompt || "(기본 프롬프트)"}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => toggle(c)} disabled={busy === c.code}
                      className={clsx(
                        "inline-flex items-center text-[11px] px-2 py-0.5 rounded",
                        c.isActive ? "bg-accent/15 text-accent" : "bg-white/5 text-white/40"
                      )}>
                      <Power size={10} className="mr-1" />{c.isActive ? "활성" : "비활성"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {isEdit ? (
                      <>
                        <button className="inline-flex p-1.5 hover:bg-accent/20 hover:text-accent rounded" onClick={save} disabled={busy === c.code}>
                          {busy === c.code ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
                        </button>
                        <button className="inline-flex p-1.5 hover:bg-white/10 rounded ml-1" onClick={cancelEdit}>
                          <X size={14} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button className="text-xs px-2 py-1 hover:bg-white/10 rounded" onClick={() => beginEdit(c)}>편집</button>
                        <button className="inline-flex p-1.5 hover:bg-danger/20 hover:text-danger rounded ml-1" onClick={() => remove(c)} disabled={busy === c.code}>
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
