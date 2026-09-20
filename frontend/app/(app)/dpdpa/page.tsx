"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type { ConsentRecord } from "@/lib/types";

export default function DpdpaPage() {
  const [records, setRecords] = useState<ConsentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRecords(await api.consent());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load consent ledger");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function erase(c: ConsentRecord) {
    if (!confirm(`Erase all data for ${c.seeker_name ?? "this seeker"}? This is irreversible (DPDPA S.7).`)) {
      return;
    }
    try {
      await api.eraseConsent(c.id);
      setRecords((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: "erased", erased_at: new Date().toISOString() } : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to erase consent");
    }
  }

  async function withdraw(c: ConsentRecord) {
    try {
      await api.withdrawConsent(c.id);
      setRecords((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: "withdrawn" } : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to withdraw consent");
    }
  }

  if (loading) return <Loading label="Loading consent ledger…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  const active = records.filter((r) => r.status === "active").length;
  const erased = records.filter((r) => r.status === "erased").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">DPDPA Consent Ledger</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Automated consent logging and right-to-erasure for employment seekers.
          </p>
        </div>
        <div className="flex space-x-2">
          <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 text-xs font-mono font-bold">
            {active} active
          </span>
          <span className="px-2.5 py-1 rounded bg-red-500/10 text-red-400 text-xs font-mono font-bold">
            {erased} erased
          </span>
        </div>
      </div>

      {records.length === 0 ? (
        <EmptyState text="No consent records yet. Seekers added to your pool are logged here automatically." />
      ) : (
        <div className="overflow-x-auto linear-card">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
                <th className="py-2.5 px-3">Job Seeker</th>
                <th className="py-2.5 px-3">Consent Basis</th>
                <th className="py-2.5 px-3">Channel</th>
                <th className="py-2.5 px-3">Retention</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
              {records.map((c) => (
                <tr key={c.id} className="hover:bg-white/[0.02]">
                  <td className="py-3 px-3 font-medium text-[#f7f8f8]">{c.seeker_name ?? `Seeker #${c.seeker_id}`}</td>
                  <td className="py-3 px-3">
                    <Badge mono>{c.basis}</Badge>
                  </td>
                  <td className="py-3 px-3">{c.channel ?? "—"}</td>
                  <td className="py-3 px-3 font-mono">{c.retention_days}d</td>
                  <td className="py-3 px-3">
                    <span
                      className={`px-2 py-0.5 rounded border text-[10px] font-medium ${
                        c.status === "active"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : c.status === "withdrawn"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-red-500/10 text-red-400 border-red-500/20"
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right space-x-2">
                    {c.status === "active" ? (
                      <>
                        <button onClick={() => withdraw(c)} className="px-2 py-1 rounded bg-white/[0.06] hover:bg-white/[0.1] text-[10px] text-[#d0d6e0]">
                          Withdraw
                        </button>
                        <button onClick={() => erase(c)} className="px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-[10px] text-red-400">
                          Erase data
                        </button>
                      </>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}