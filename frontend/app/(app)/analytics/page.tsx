"use client";

import { useCallback, useEffect, useState } from "react";

import { MetricCard } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type {
  FunnelData,
  RevenueData,
  PipelineVelocityData,
  SkillsDemandData,
  SourceROIData,
  TimeToFillData,
} from "@/lib/types";

const TABS = ["Funnel", "Time-to-Fill", "Source ROI", "Revenue", "Skills", "Pipeline"] as const;
type Tab = (typeof TABS)[number];

const PERIODS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
  { label: "All time", value: 3650 },
];

function BarChart({ items, max }: { items: { label: string; value: number }[]; max?: number }) {
  const m = max ?? Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center space-x-3">
          <span className="w-28 text-[11px] text-[#8a8f98] truncate text-right">{item.label}</span>
          <div className="flex-1 bg-white/[0.04] h-5 rounded overflow-hidden">
            <div
              className="h-full bg-brand/60 rounded flex items-center justify-end pr-2"
              style={{ width: `${Math.max((item.value / m) * 100, 2)}%` }}
            >
              <span className="text-[10px] font-mono text-white/80">{item.value}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function FunnelTab({ data }: { data: FunnelData }) {
  const max = Math.max(...data.stages.map((s) => s.count), 1);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-5 gap-3">
        {data.stages.map((s, i) => {
          const pct = i > 0 && data.stages[0].count > 0
            ? Math.round((s.count / data.stages[0].count) * 100)
            : 100;
          return (
            <div key={s.name} className="linear-card p-4 text-center">
              <div className="text-[11px] text-[#8a8f98] mb-1">{s.name}</div>
              <div className="text-xl font-semibold text-[#f7f8f8]">{s.count}</div>
              <div className="text-[10px] text-[#62666d] font-mono">{pct}% of applied</div>
              <div className="mt-2 w-full bg-white/[0.06] h-1.5 rounded-full overflow-hidden">
                <div className="bg-brand/60 h-full rounded" style={{ width: `${(s.count / max) * 100}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TimeToFillTab({ data }: { data: TimeToFillData }) {
  const items = Object.entries(data.by_contract).map(([k, v]) => ({ label: k, value: v }));
  return (
    <div className="space-y-4">
      <MetricCard label="Average Days to Fill" value={data.avg_days} hint={<span className="text-brand-light font-mono text-[10px]">{data.count} placements</span>} />
      {items.length > 0 ? (
        <div className="linear-card p-5 space-y-3">
          <h3 className="text-sm font-semibold">By Contract</h3>
          <BarChart items={items} />
        </div>
      ) : (
        <EmptyState text="No placement data yet" />
      )}
    </div>
  );
}

function SourceROITab({ data }: { data: SourceROIData }) {
  return (
    <div className="linear-card p-5 space-y-4">
      <h3 className="text-sm font-semibold">Sourcing Channel ROI</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
              <th className="py-2.5 px-3">Source</th>
              <th className="py-2.5 px-3">Candidates</th>
              <th className="py-2.5 px-3">Hires</th>
              <th className="py-2.5 px-3">Conversion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
            {data.sources.map((s) => (
              <tr key={s.source} className="hover:bg-white/[0.02]">
                <td className="py-3 px-3 font-medium text-[#f7f8f8]">{s.source}</td>
                <td className="py-3 px-3 font-mono">{s.total_candidates}</td>
                <td className="py-3 px-3 font-mono text-emerald-400">{s.hires}</td>
                <td className="py-3 px-3">
                  <span className={`font-mono ${s.conversion_rate > 10 ? "text-emerald-400" : "text-[#8a8f98]"}`}>
                    {s.conversion_rate}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RevenueTab({ data }: { data: RevenueData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard label="Total Placements" value={data.total_placements} />
        <MetricCard label="Avg Bill Rate" value={`₹${data.avg_bill_rate.toLocaleString()}`} />
        <MetricCard label="Revenue (Est.)" value={`₹${data.total_revenue_est.toLocaleString()}`} />
      </div>
      {data.monthly_trend.length > 0 ? (
        <div className="linear-card p-5 space-y-3">
          <h3 className="text-sm font-semibold">Monthly Trend</h3>
          <div className="space-y-2">
            {data.monthly_trend.map((m) => (
              <div key={m.month} className="flex items-center space-x-3">
                <span className="w-20 text-[11px] text-[#8a8f98] font-mono">{m.month}</span>
                <span className="w-16 text-[11px] text-[#f7f8f8] font-mono">{m.placements}</span>
                <span className="text-[11px] text-emerald-400 font-mono">₹{m.revenue.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState text="No revenue data yet" />
      )}
    </div>
  );
}

function SkillsTab({ data }: { data: SkillsDemandData }) {
  const items = data.skills.slice(0, 15).map((s) => ({ label: s.skill, value: s.demand }));
  return (
    <div className="space-y-4">
      <div className="linear-card p-5 space-y-3">
        <h3 className="text-sm font-semibold">Top In-Demand Skills</h3>
        {items.length > 0 ? <BarChart items={items} /> : <EmptyState text="No skills data yet" />}
      </div>
      <div className="linear-card p-5 space-y-3">
        <h3 className="text-sm font-semibold">Supply vs Demand Gap</h3>
        <div className="space-y-2">
          {data.skills.slice(0, 15).map((s) => (
            <div key={s.skill} className="flex items-center space-x-3 text-[11px]">
              <span className="w-28 text-right text-[#8a8f98] truncate">{s.skill}</span>
              <span className="w-12 text-center font-mono text-blue-400">{s.supply}</span>
              <span className="w-4 text-center text-[#62666d]">/</span>
              <span className="w-12 text-center font-mono text-amber-400">{s.demand}</span>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                  s.status === "shortage"
                    ? "bg-red-500/10 text-red-400"
                    : s.status === "surplus"
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-white/[0.06] text-[#8a8f98]"
                }`}
              >
                {s.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PipelineTab({ data }: { data: PipelineVelocityData }) {
  const items = data.stages.map((s) => ({ label: s.stage, value: s.avg_days }));
  return (
    <div className="space-y-4">
      {data.bottleneck && (
        <div className="p-3 rounded bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
          Bottleneck detected: <span className="font-mono font-bold">{data.bottleneck}</span>
        </div>
      )}
      <div className="linear-card p-5 space-y-3">
        <h3 className="text-sm font-semibold">Avg Days in Each Stage</h3>
        {items.length > 0 ? <BarChart items={items} /> : <EmptyState text="No pipeline data yet" />}
      </div>
      <div className="linear-card p-5 space-y-3">
        <h3 className="text-sm font-semibold">Stage Details</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
                <th className="py-2.5 px-3">Stage</th>
                <th className="py-2.5 px-3">Avg Days</th>
                <th className="py-2.5 px-3">Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
              {data.stages.map((s) => (
                <tr key={s.stage} className="hover:bg-white/[0.02]">
                  <td className="py-3 px-3 font-medium text-[#f7f8f8]">{s.stage}</td>
                  <td className="py-3 px-3 font-mono">{s.avg_days}</td>
                  <td className="py-3 px-3 font-mono">{s.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function exportCSV(data: any[], filename: string) {
  if (data.length === 0) return;
  const headers = Object.keys(data[0]);
  const csv = [headers.join(","), ...data.map((row: Record<string, unknown>) => headers.map((h) => JSON.stringify(row[h] ?? "")).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>("Funnel");
  const [period, setPeriod] = useState(30);
  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [ttf, setTtf] = useState<TimeToFillData | null>(null);
  const [roi, setRoi] = useState<SourceROIData | null>(null);
  const [revenue, setRevenue] = useState<RevenueData | null>(null);
  const [skills, setSkills] = useState<SkillsDemandData | null>(null);
  const [pipeline, setPipeline] = useState<PipelineVelocityData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [f, t, r, rev, s, p] = await Promise.all([
        api.analyticsFunnel(period),
        api.analyticsTimeToFill(period),
        api.analyticsSourceROI(period),
        api.analyticsRevenue(period),
        api.analyticsSkillsDemand(),
        api.analyticsPipelineVelocity(period),
      ]);
      setFunnel(f);
      setTtf(t);
      setRoi(r);
      setRevenue(rev);
      setSkills(s);
      setPipeline(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    load();
  }, [load]);

  function handleExport() {
    let data: unknown[] | undefined;
    let name = "export.csv";
    if (tab === "Funnel") { data = funnel?.stages; name = "funnel.csv"; }
    else if (tab === "Source ROI") { data = roi?.sources; name = "source-roi.csv"; }
    else if (tab === "Revenue") { data = revenue?.monthly_trend; name = "revenue.csv"; }
    else if (tab === "Skills") { data = skills?.skills; name = "skills-demand.csv"; }
    else if (tab === "Pipeline") { data = pipeline?.stages; name = "pipeline-velocity.csv"; }
    if (data) exportCSV(data as Record<string, unknown>[], name);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Advanced Analytics</h1>
          <p className="text-xs text-[#8a8f98] mt-1">Recruitment funnel, time-to-fill, ROI, and pipeline insights.</p>
        </div>
        <div className="flex items-center space-x-2">
          <select
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
            className="bg-white/[0.06] border border-white/10 rounded px-2 py-1 text-xs text-[#f7f8f8]"
          >
            {PERIODS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <button
            onClick={handleExport}
            className="px-3 py-1.5 rounded bg-white/[0.06] border border-white/10 text-xs text-[#8a8f98] hover:text-white transition"
          >
            Export CSV
          </button>
        </div>
      </div>

      <div className="flex space-x-1 border-b border-white/[0.08] pb-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-xs font-medium rounded transition ${
              tab === t ? "bg-brand/20 text-brand-light" : "text-[#8a8f98] hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <Loading label="Loading analytics…" />
      ) : error ? (
        <ErrorBanner message={error} onRetry={load} />
      ) : (
        <div>
          {tab === "Funnel" && funnel && <FunnelTab data={funnel} />}
          {tab === "Time-to-Fill" && ttf && <TimeToFillTab data={ttf} />}
          {tab === "Source ROI" && roi && <SourceROITab data={roi} />}
          {tab === "Revenue" && revenue && <RevenueTab data={revenue} />}
          {tab === "Skills" && skills && <SkillsTab data={skills} />}
          {tab === "Pipeline" && pipeline && <PipelineTab data={pipeline} />}
        </div>
      )}
    </div>
  );
}
