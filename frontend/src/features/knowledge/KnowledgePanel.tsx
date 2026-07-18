import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BookOpen, Clock3, Database, Layers3, Plus, RefreshCw, ThumbsUp, X } from "lucide-react";
import type { KnowledgeArticle, KnowledgeArticleListResponse, KnowledgeStats, KnowledgeVersion } from "@/shared/types";

type ViewTab = "overview" | "assets" | "gaps";
type AssetStatus = "all" | "draft" | "approved" | "rejected";

const STATUS_STYLE: Record<string, string> = {
  approved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  draft: "bg-amber-50 text-amber-700 ring-amber-200",
  rejected: "bg-rose-50 text-rose-700 ring-rose-200",
  gap: "bg-orange-50 text-orange-700 ring-orange-200",
};
const STATUS_LABEL: Record<string, string> = { approved: "已发布", draft: "待审核", rejected: "已拒绝", gap: "知识缺口" };

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...options, headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) } });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail || `请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const percent = (value: number) => `${Math.round(value * 100)}%`;
const formatTime = (value?: string | null) => value ? new Date(value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";

const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLE[status] ?? "bg-gray-50 text-gray-600 ring-gray-200"}`}>
    {STATUS_LABEL[status] ?? status}
  </span>
);

interface MetricCardProps { label: string; value: string | number; hint: string; icon: React.ReactNode; tone: string }
const MetricCard: React.FC<MetricCardProps> = ({ label, value, hint, icon, tone }) => (
  <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
    <div className="flex items-start justify-between"><div><p className="text-xs font-medium text-gray-500">{label}</p><p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p></div><div className={`rounded-xl p-2.5 ${tone}`}>{icon}</div></div>
    <p className="mt-3 text-xs text-gray-400">{hint}</p>
  </div>
);

const Overview: React.FC<{ stats: KnowledgeStats | null }> = ({ stats }) => {
  const answerRate = stats?.retrievals_24h ? stats.answered_retrievals_24h / stats.retrievals_24h : 0;
  return <div className="space-y-5">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="已发布知识" value={stats?.total_approved ?? 0} hint={`全部知识资产 ${stats?.total_articles ?? 0} 条`} icon={<BookOpen className="h-5 w-5" />} tone="bg-blue-50 text-blue-600" />
      <MetricCard label="待审核" value={stats?.total_drafts ?? 0} hint={`已隔离 ${stats?.total_rejected ?? 0} 条`} icon={<Clock3 className="h-5 w-5" />} tone="bg-amber-50 text-amber-600" />
      <MetricCard label="知识缺口" value={stats?.total_gaps ?? 0} hint="等待运营人员补充答案" icon={<AlertTriangle className="h-5 w-5" />} tone="bg-orange-50 text-orange-600" />
      <MetricCard label="知识分块" value={stats?.total_chunks ?? 0} hint={`共 ${stats?.total_versions ?? 0} 个不可变版本`} icon={<Layers3 className="h-5 w-5" />} tone="bg-violet-50 text-violet-600" />
    </div>
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 lg:col-span-2">
        <h3 className="text-sm font-semibold text-gray-900">知识自进化闭环</h3>
        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          {[["1","采集","会话、工单、人工录入"],["2","治理","去重、审核、版本化"],["3","发布","分块并同步向量索引"],["4","评估","检索事件与真实反馈"]].map(([step,title,text]) => <div key={step} className="rounded-xl bg-gray-50 p-3"><span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-900 text-xs text-white">{step}</span><p className="mt-3 text-sm font-medium text-gray-800">{title}</p><p className="mt-1 text-xs leading-5 text-gray-500">{text}</p></div>)}
        </div>
      </div>
      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">近 24 小时质量</h3>
        <div className="mt-4 space-y-4">
          <div><div className="flex justify-between text-xs text-gray-500"><span>有效回答率</span><span>{percent(answerRate)}</span></div><div className="mt-2 h-2 rounded-full bg-gray-100"><div className="h-2 rounded-full bg-blue-500" style={{ width: percent(answerRate) }} /></div></div>
          <div className="flex items-center justify-between rounded-xl bg-gray-50 px-3 py-2.5"><span className="flex items-center gap-2 text-xs text-gray-500"><Activity className="h-4 w-4" />检索次数</span><strong className="text-sm text-gray-800">{stats?.retrievals_24h ?? 0}</strong></div>
          <div className="flex items-center justify-between rounded-xl bg-gray-50 px-3 py-2.5"><span className="flex items-center gap-2 text-xs text-gray-500"><ThumbsUp className="h-4 w-4" />反馈有用率</span><strong className="text-sm text-gray-800">{percent(stats?.helpful_rate ?? 0)}</strong></div>
        </div>
      </div>
    </div>
  </div>;
};

interface AssetDetailProps { article: KnowledgeArticle; versions: KnowledgeVersion[]; busy: boolean; onApprove: () => void; onReject: () => void }
const AssetDetail: React.FC<AssetDetailProps> = ({ article, versions, busy, onApprove, onReject }) => (
  <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
    <div className="flex items-start justify-between gap-3"><div><StatusBadge status={article.status} /><h3 className="mt-3 text-lg font-semibold text-gray-900">{article.title}</h3><p className="mt-1 text-xs text-gray-400">{article.canonical_key}</p></div><span className="rounded-lg bg-gray-50 px-2 py-1 text-xs text-gray-500">v{article.current_version}</span></div>
    <div className="mt-4 flex flex-wrap gap-1.5">{(article.tags ?? []).map(tag => <span key={tag} className="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700">{tag}</span>)}</div>
    <div className="mt-5 rounded-xl bg-gray-50 p-4 text-sm leading-6 text-gray-700 whitespace-pre-wrap">{article.content || "暂无内容"}</div>
    <dl className="mt-5 grid grid-cols-2 gap-3 text-xs">{[["来源",article.source_type],["负责人",article.owner],["分类",article.category || "other"],["质量分",percent(article.quality_score || 0)],["使用次数",String(article.usage_count)],["发布时间",formatTime(article.published_at)]].map(([label,value]) => <div key={label} className="rounded-lg border border-gray-100 p-2.5"><dt className="text-gray-400">{label}</dt><dd className="mt-1 font-medium text-gray-700">{value}</dd></div>)}</dl>
    {article.status === "draft" && <div className="mt-5 flex gap-2 border-t pt-4"><button onClick={onApprove} disabled={busy} className="flex-1 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">审核并发布</button><button onClick={onReject} disabled={busy} className="rounded-xl bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 disabled:opacity-50">拒绝</button></div>}
    <div className="mt-6 border-t pt-4"><h4 className="text-sm font-semibold text-gray-800">版本历史</h4><div className="mt-3 space-y-2">{versions.map(version => <div key={version.id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-xs"><span className="font-medium text-gray-700">v{version.version_number} · {version.change_summary || "内容版本"}</span><span className="text-gray-400">{formatTime(version.created_at)}</span></div>)}{versions.length === 0 && <p className="text-xs text-gray-400">暂无版本记录</p>}</div></div>
  </div>
);

const ManualForm: React.FC<{ onClose: () => void; onCreated: () => void }> = ({ onClose, onCreated }) => {
  const [title,setTitle] = useState(""); const [content,setContent] = useState(""); const [category,setCategory] = useState("other"); const [tags,setTags] = useState(""); const [busy,setBusy] = useState(false);
  const submit = async () => { if (!title.trim() || !content.trim()) return; setBusy(true); try { await api("/api/v1/knowledge/articles", { method:"POST", body:JSON.stringify({ title:title.trim(), content:content.trim(), category, tags:tags.split(/[,，]/).map(tag => tag.trim()).filter(Boolean), owner:"operator" }) }); onCreated(); } finally { setBusy(false); } };
  return <div className="rounded-2xl border border-blue-200 bg-blue-50/40 p-5"><div className="flex items-center justify-between"><h3 className="font-semibold text-gray-900">新建知识草稿</h3><button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-white"><X className="h-4 w-4" /></button></div><div className="mt-4 grid gap-3 sm:grid-cols-2"><input value={title} onChange={e => setTitle(e.target.value)} placeholder="知识标题" className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm" /><input value={category} onChange={e => setCategory(e.target.value)} placeholder="分类" className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm" /><input value={tags} onChange={e => setTags(e.target.value)} placeholder="标签，用逗号分隔" className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm sm:col-span-2" /><textarea value={content} onChange={e => setContent(e.target.value)} placeholder="标准答案或操作说明" rows={5} className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm sm:col-span-2" /></div><button onClick={submit} disabled={busy || !title.trim() || !content.trim()} className="mt-3 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">保存为待审核草稿</button></div>;
};

const GapList: React.FC<{ gaps: KnowledgeArticle[]; onFilled: () => void }> = ({ gaps, onFilled }) => {
  const [activeId,setActiveId] = useState<string | null>(null); const [content,setContent] = useState(""); const [category,setCategory] = useState("other"); const [busy,setBusy] = useState(false); const active = gaps.find(gap => gap.id === activeId) ?? null;
  const fill = async () => { if (!active || !content.trim()) return; setBusy(true); try { await api(`/api/v1/knowledge/gaps/${active.id}/fill`, { method:"POST", body:JSON.stringify({ content:content.trim(), category, tags:["人工补全"] }) }); setActiveId(null); setContent(""); onFilled(); } finally { setBusy(false); } };
  if (gaps.length === 0) return <div className="rounded-2xl border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">当前没有待处理的知识缺口</div>;
  return <div className="grid gap-4 lg:grid-cols-2"><div className="space-y-3">{gaps.map(gap => <button key={gap.id} onClick={() => { setActiveId(gap.id); setCategory(gap.category || "other"); }} className={`w-full rounded-2xl border bg-white p-4 text-left transition ${activeId === gap.id ? "border-orange-400 ring-2 ring-orange-100" : "border-gray-200 hover:border-gray-300"}`}><div className="flex items-start justify-between gap-3"><div><StatusBadge status="gap" /><p className="mt-2 text-sm font-medium text-gray-900">{gap.title}</p></div><span className="text-xs text-gray-400">{formatTime(gap.created_at)}</span></div><p className="mt-3 text-xs text-gray-500">最高检索相关度：{percent(Number(gap.metadata?.top_retrieval_score ?? 0))}</p></button>)}</div><div>{active ? <div className="rounded-2xl border border-orange-200 bg-white p-5 shadow-sm"><h3 className="font-semibold text-gray-900">补全知识缺口</h3><p className="mt-2 rounded-xl bg-orange-50 p-3 text-sm text-orange-900">{active.title}</p><input value={category} onChange={e => setCategory(e.target.value)} className="mt-3 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm" placeholder="分类" /><textarea value={content} onChange={e => setContent(e.target.value)} rows={8} className="mt-3 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm" placeholder="填写经过确认的标准答案" /><button onClick={fill} disabled={busy || !content.trim()} className="mt-3 w-full rounded-xl bg-orange-600 py-2 text-sm font-medium text-white disabled:opacity-50">发布答案并关闭缺口</button></div> : <div className="rounded-2xl border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">选择一条缺口开始补全</div>}</div></div>;
};

export const KnowledgePanel: React.FC = () => {
  const [tab,setTab] = useState<ViewTab>("overview"); const [stats,setStats] = useState<KnowledgeStats | null>(null); const [articles,setArticles] = useState<KnowledgeArticle[]>([]); const [gaps,setGaps] = useState<KnowledgeArticle[]>([]); const [status,setStatus] = useState<AssetStatus>("all"); const [selectedId,setSelectedId] = useState<string | null>(null); const [versions,setVersions] = useState<KnowledgeVersion[]>([]); const [loading,setLoading] = useState(true); const [busy,setBusy] = useState(false); const [error,setError] = useState<string | null>(null); const [showCreate,setShowCreate] = useState(false);
  const load = useCallback(async () => { setLoading(true); setError(null); try { const statusQuery = status === "all" ? "" : `&status=${status}`; const [statsData,articleData,gapData] = await Promise.all([api<KnowledgeStats>("/api/v1/knowledge/stats"),api<KnowledgeArticleListResponse>(`/api/v1/knowledge/articles?page=1&page_size=100${statusQuery}`),api<KnowledgeArticleListResponse>("/api/v1/knowledge/gaps?page=1&page_size=100")]); setStats(statsData); setArticles(articleData.articles); setGaps(gapData.articles); if (selectedId && !articleData.articles.some(article => article.id === selectedId)) setSelectedId(null); } catch (cause) { setError(cause instanceof Error ? cause.message : "数据加载失败"); } finally { setLoading(false); } }, [selectedId,status]);
  useEffect(() => { void load(); }, [load]);
  const selected = useMemo(() => articles.find(article => article.id === selectedId) ?? null, [articles,selectedId]);
  useEffect(() => { if (!selectedId) { setVersions([]); return; } void api<KnowledgeVersion[]>(`/api/v1/knowledge/articles/${selectedId}/versions`).then(setVersions).catch(() => setVersions([])); }, [selectedId]);
  const act = async (action:"approve"|"reject") => { if (!selected) return; setBusy(true); try { await api(`/api/v1/knowledge/articles/${selected.id}/${action}`, { method:"POST", body:action === "reject" ? JSON.stringify({ reason:"运营审核未通过" }) : undefined }); setSelectedId(null); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : "操作失败"); } finally { setBusy(false); } };
  const tabs:Array<{id:ViewTab;label:string;count?:number}> = [{id:"overview",label:"运营概览"},{id:"assets",label:"知识资产",count:stats?.total_articles},{id:"gaps",label:"缺口治理",count:stats?.total_gaps}];
  return <div className="mx-auto max-w-7xl space-y-5"><div className="flex flex-col gap-4 rounded-2xl bg-gray-950 px-5 py-5 text-white sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><div className="rounded-xl bg-white/10 p-2.5"><Database className="h-6 w-6" /></div><div><h1 className="text-xl font-semibold">知识数据中台</h1><p className="mt-1 text-sm text-gray-400">采集、治理、发布、评估一体化的知识自进化控制台</p></div></div><div className="flex gap-2"><button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-3 py-2 text-sm font-medium hover:bg-blue-500"><Plus className="h-4 w-4" />新建知识</button><button onClick={() => void load()} className="rounded-xl bg-white/10 p-2.5 hover:bg-white/20" aria-label="刷新"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /></button></div></div><div className="flex gap-1 rounded-xl border border-gray-200 bg-white p-1">{tabs.map(item => <button key={item.id} onClick={() => setTab(item.id)} className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${tab === item.id ? "bg-gray-900 text-white" : "text-gray-500 hover:bg-gray-50"}`}>{item.label}{item.count !== undefined && <span className="ml-1.5 opacity-70">{item.count}</span>}</button>)}</div>{error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}{showCreate && <ManualForm onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); setTab("assets"); void load(); }} />}{tab === "overview" && <Overview stats={stats} />}{tab === "assets" && <div className="space-y-4"><div className="flex items-center justify-between"><select value={status} onChange={e => setStatus(e.target.value as AssetStatus)} className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm"><option value="all">全部状态</option><option value="draft">待审核</option><option value="approved">已发布</option><option value="rejected">已拒绝</option></select><span className="text-xs text-gray-400">当前 {articles.length} 条</span></div><div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)]"><div className="space-y-2">{articles.map(article => <button key={article.id} onClick={() => setSelectedId(article.id)} className={`w-full rounded-xl border bg-white p-4 text-left ${selectedId === article.id ? "border-blue-400 ring-2 ring-blue-100" : "border-gray-200 hover:border-gray-300"}`}><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-medium text-gray-900">{article.title}</p><p className="mt-1 text-xs text-gray-400">{article.source_type} · {article.owner}</p></div><StatusBadge status={article.status} /></div><div className="mt-3 flex items-center gap-4 text-xs text-gray-500"><span>v{article.current_version}</span><span>使用 {article.usage_count}</span><span>质量 {percent(article.quality_score || 0)}</span></div></button>)}{!loading && articles.length === 0 && <div className="rounded-xl border border-dashed border-gray-300 bg-white py-14 text-center text-sm text-gray-400">暂无知识资产</div>}</div>{selected ? <AssetDetail article={selected} versions={versions} busy={busy} onApprove={() => void act("approve")} onReject={() => void act("reject")} /> : <div className="rounded-2xl border border-dashed border-gray-300 bg-white py-20 text-center text-sm text-gray-400">选择知识资产查看治理详情</div>}</div></div>}{tab === "gaps" && <GapList gaps={gaps} onFilled={() => void load()} />}</div>;
};

export default KnowledgePanel;
