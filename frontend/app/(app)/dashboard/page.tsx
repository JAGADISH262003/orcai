"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { MetricCard } from "@/components/Badge";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type { Contract, Dashboard as DashboardData, Match, Seeker } from "@/lib/types";

export default function DashboardPage() {
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [seekers, setSeekers] = useState<Seeker[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [d, c, s, m] = await Promise.all([
        api.dashboard(),
        api.contracts(),
        api.seekers(),
        api.matches("?limit=6"),
      ]);
      setDash(d);
      setContracts(c);
      setSeekers(s);
      setMatches(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <Loading label="Loading command center…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;
  if (!dash) return <EmptyState text="No data yet" />;

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">ORCAI Command Center</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Employer contracts matched against verified employment seekers in real time.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Active Employer Requisitions"
            value={dash.active_contracts}
            hint={<span className="text-emerald-400 font-mono text-[10px]">live</span>}
            sub={
              <>
                <span>Avg AI match score:</span>
                <span className="text-[#d0d6e0] font-mono">{dash.avg_match_score}%</span>
              </>
            }
          />
          <MetricCard
            label="Talent Pool Inbound (Supply)"
            value={dash.total_seekers}
            hint={<span className="text-brand-light font-mono text-[10px]">auto-parsed</span>}
            sub={
              <>
                <span>Tier-A matches:</span>
                <span className="text-emerald-400 font-mono">{dash.tier_a_matches}</span>
              </>
            }
          />
          <MetricCard
            label="HITL Confidence Queue"
            value={dash.pending_hitl}
            accent="text-amber-400"
            hint={<span className="text-amber-400 font-mono text-[10px]">review needed</span>}
            sub={
              <>
                <Link href="/hitl" className="text-brand-light hover:underline">
                  Open review queue →
                </Link>
              </>
            }
          />
          <MetricCard
            label="Matches Computed"
            value={dash.matches_this_week}
            hint={<span className="text-purple-400 font-mono text-[10px]">this cycle</span>}
            sub={
              <>
                <span>Engine:</span>
                <span className="text-[#d0d6e0] font-mono">deterministic + AI</span>
              </>
            }
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 linear-card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Active Contracts & Top Matches</h2>
              <Link href="/pipeline" className="text-xs text-brand-light hover:underline">
                View board →
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
                    <th className="py-2.5 px-3">Candidate</th>
                    <th className="py-2.5 px-3">Client Contract</th>
                    <th className="py-2.5 px-3">Rate / CTC</th>
                    <th className="py-2.5 px-3">AI Score</th>
                    <th className="py-2.5 px-3">Stage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
                  {matches.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-[#62666d]">
                        Run the matching engine to see top matches.
                      </td>
                    </tr>
                  ) : (
                    matches.slice(0, 5).map((m) => (
                      <tr key={m.id} className="hover:bg-white/[0.02]">
                        <td className="py-3 px-3 font-medium text-[#f7f8f8]">
                          {m.seeker_name ?? "—"}
                          {m.seeker_headline ? (
                            <div className="text-[10px] text-[#8a8f98] font-normal">
                              {m.seeker_headline}
                            </div>
                          ) : null}
                        </td>
                        <td className="py-3 px-3">{m.contract_title ?? "—"}</td>
                        <td className="py-3 px-3 font-mono">
                          {m.status === "placed" ? "Placed ✓" : m.status}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`font-mono font-bold ${
                              m.tier === "A" ? "text-emerald-400" : m.tier === "B" ? "text-amber-400" : "text-[#8a8f98]"
                            }`}
                          >
                            {m.score}%
                          </span>{" "}
                          <span className="text-[10px] text-[#8a8f98]">Tier {m.tier}</span>
                        </td>
                        <td className="py-3 px-3">
                          {m.hitl_required ? (
                            <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[10px]">
                              HITL review
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded bg-white/[0.06] text-[#8a8f98] text-[10px]">
                              {m.status}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-4">
            <div className="linear-card p-5 space-y-4">
              <h2 className="text-sm font-semibold">3-Tier Waterfall Sourcing</h2>
              <div className="space-y-3 text-xs">
                {[
                  { name: "Tier 1: Free Inbound", cost: "₹0 / mo", pct: 80, color: "bg-emerald-400", note: "Indeed, Telegram, WhatsApp" },
                  { name: "Tier 2: Consultancy DB", cost: "₹0 marginal", pct: 45, color: "bg-blue-400", note: "Bulk CSV/ZIP + DPDPA affidavit" },
                  { name: "Tier 3: Enrichment APIs", cost: "₹1,200 cap", pct: 20, color: "bg-amber-400", note: "Apollo/PDL for Tier-A only" },
                ].map((t) => (
                  <div key={t.name} className="p-3 rounded bg-white/[0.02] border border-white/[0.06]">
                    <div className="flex justify-between font-medium text-[#f7f8f8] mb-1">
                      <span>{t.name}</span>
                      <span className="text-emerald-400 font-mono">{t.cost}</span>
                    </div>
                    <p className="text-[11px] text-[#8a8f98]">{t.note}</p>
                    <div className="mt-2 w-full bg-white/[0.06] h-1.5 rounded-full overflow-hidden">
                      <div className={`${t.color} h-full`} style={{ width: `${t.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <Link
                href="/seekers"
                className="w-full block text-center py-2 bg-brand/20 hover:bg-brand/30 text-brand-light text-xs font-medium rounded transition"
              >
                Open Ingestion Wizard →
              </Link>
            </div>

            <div className="linear-card p-5 space-y-3">
              <h2 className="text-sm font-semibold">Supply Snapshot</h2>
              <div className="flex justify-between text-xs">
                <span className="text-[#8a8f98]">Active seekers</span>
                <span className="font-mono text-[#f7f8f8]">{seekers.length}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-[#8a8f98]">Active contracts</span>
                <span className="font-mono text-[#f7f8f8]">{contracts.filter((c) => c.status === "active").length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}