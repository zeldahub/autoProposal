import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Folder, Package, FileText, FileSpreadsheet } from "lucide-react";
import { listProjects, listAllArtifacts, type ArtifactItem } from "../api/client";
import { formatDate, shortUuid } from "../lib/format";
import StatusBadge from "../components/StatusBadge";

export default function Dashboard() {
  const [projTotal, setProjTotal] = useState(0);
  const [artTotal, setArtTotal] = useState(0);
  const [recentProjects, setRecentProjects] = useState<any[]>([]);
  const [recentArtifacts, setRecentArtifacts] = useState<ArtifactItem[]>([]);

  useEffect(() => {
    Promise.all([
      listProjects(0, 5),
      listAllArtifacts({ page: 0, size: 5 }),
    ]).then(([p, a]) => {
      setProjTotal(p.total);
      setRecentProjects(p.items);
      setArtTotal(a.total);
      setRecentArtifacts(a.items);
    }).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 max-w-6xl">
      <h1 className="text-2xl font-bold">홈</h1>

      <div className="grid grid-cols-3 gap-4">
        <Card to="/generator" Icon={Sparkles} title="신규 사업제안서" desc="공고문 분석부터 PPTX 생성까지" />
        <Card to="/projects" Icon={Folder} title={`사업 관리 (${projTotal})`} desc="저장된 사업 목록" />
        <Card to="/artifacts" Icon={Package} title={`산출물 (${artTotal})`} desc="PPTX / WBS 라이브러리" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <section className="card">
          <h2 className="section-title">최근 사업</h2>
          {recentProjects.length === 0 ? (
            <div className="text-sm text-white/40 py-4 text-center">아직 없음</div>
          ) : (
            <ul className="space-y-1">
              {recentProjects.map((p) => (
                <li key={p.uuid}>
                  <Link to={`/projects/${p.uuid}`} className="flex items-center gap-2 text-sm py-2 px-2 -mx-2 rounded hover:bg-white/5">
                    <span className="font-mono text-xs text-white/30 w-16">{shortUuid(p.uuid)}</span>
                    <span className="flex-1 truncate">{p.projectName}</span>
                    <StatusBadge status={p.status} />
                    <span className="text-[11px] text-white/40 w-32 text-right">{formatDate(p.updatedAt)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <h2 className="section-title">최근 산출물</h2>
          {recentArtifacts.length === 0 ? (
            <div className="text-sm text-white/40 py-4 text-center">아직 없음</div>
          ) : (
            <ul className="space-y-1">
              {recentArtifacts.map((a) => {
                const Icon = a.type === "PPTX" ? FileText : FileSpreadsheet;
                return (
                  <li key={a.id}>
                    <Link to={`/projects/${a.projectUuid}`} className="flex items-center gap-2 text-sm py-2 px-2 -mx-2 rounded hover:bg-white/5">
                      <Icon size={14} className="text-primary" />
                      <span className="flex-1 truncate">{a.projectName} <span className="text-white/40">v{a.version}</span></span>
                      <span className="text-[11px] text-white/40">{formatDate(a.createdAt)}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function Card({ title, desc, to, Icon }: { title: string; desc: string; to: string; Icon: any }) {
  return (
    <Link to={to} className="card hover:border-primary/40 transition block">
      <Icon className="text-primary mb-3" />
      <div className="font-semibold">{title}</div>
      <div className="text-xs text-white/50 mt-1">{desc}</div>
    </Link>
  );
}
