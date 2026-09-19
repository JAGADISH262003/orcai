"use client";

import { useEffect, useState } from "react";

import { TierBadge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api, pollJob } from "@/lib/client";
import type { Contract, Match, WorkflowStage } from "@/lib/types";
import { useApp } from "@/components/AppShell";

const TONE = [
  "border-amber-500/40",
  "border-blue-500/40",
  "border-purple-500/40",
  "border-brand/40",
  "border-teal-500/40",
  "border-cyan-500/40",
  "border-emerald-500/40",
];

const REJECT_TONE = "border-red-500/40";

export default function PipelinePage() {
  const { session } = useApp();
  const workflow = session?.agency?.workflow;
  const stages: WorkflowStage[] = workflow?.stages ?? [];
  const fillKey = workflow?.fill_stage ?? "placed";
  const rejectKey = workflow?.reject_stage ?? "rejected";

  const columns = [
    ...stages.map((s, i) => ({
      key: s.key,
      label: s.label,
      tone: TONE[i % TONE.length],
      isTerminal: s.key === fillKey,
      isEntry: s.key === workflow?.entry_stage,
    })),
    { key: rejectKey, label: "Rejected", tone: REJECT_TONE, isTerminal: false, isEntry: false },
  ];

  const [matches, setMatches] = useState<Match[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [contractFilter, setContractFilter] = useState<number | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (contractFilter) params.set("contract_id", String(contractFilter));
      setMatches(await api.matches(`?${params.toString()}`));
      setContracts(await api.contracts());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [contractFilter]);

  function getNextStageKey(currentKey: string): string | null {
    const keys = stages.map((s) => s.key);
    const idx = keys.indexOf(currentKey);
    if (idx < 0 || idx >= keys.length - 1) return null;
    return keys[idx + 1];
  }

  async function advance(m: Match, next: string) {
    await api.setMatchStatus(m.id, next);
    setMatches((prev) => prev.map((x) => (x.id === m.id ? { ...x, status: next } : x)));
  }

  const grouped = columns.map((col) => ({
    ...col,
    items: matches.filter((m) => m.status === col.key),
  }));

  if (loading) return <Loading label="Loading pipeline…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {workflow?.label ?? "Matching & Submissions Pipeline"}
          </h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            {workflow?.description ?? "Seeker-candidate matches flowing from AI scoring to placement."}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <select
            value={contractFilter}
            onChange={(e) => setContractFilter(e.target.value ? Number(e.target.value) : "")}
            className="linear-input px-3 py-1.5 text-xs"
          >
            <option value="">All contracts</option>
            {contracts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title ?? c.id}
              </option>
            ))}
          </select>
          <button
            onClick={async () => {
              setLoading(true);
              try {
                const job = await api.runMatching();
                await pollJob(job.id);
                await load();
              } finally {
                setLoading(false);
              }
            }}
            className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition"
          >
            Re-run matching
          </button>
        </div>
      </div>

      {matches.length === 0 ? (
        <EmptyState
          text="No matches yet — post a contract and run the matching engine."
          action={
            <button
              onClick={async () => {
                const job = await api.runMatching();
                await pollJob(job.id);
                await load();
              }}
              className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium"
            >
              Run matching engine
            </button>
          }
        />
      ) : (
        <div
          className="grid gap-4"
          style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}
        >
          {grouped.map((col) => (
            <div key={col.key} className={`linear-card p-4 space-y-3 bg-[#0f1011] border-t-2 ${col.tone}`}>
              <div className="flex justify-between items-center pb-2 border-b border-white/[0.08] text-xs font-semibold">
                <span>{col.label}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-[#8a8f98]">
                  {col.items.length}
                </span>
              </div>
              {col.items.length === 0 ? (
                <p className="text-[11px] text-[#62666d] py-4 text-center">Empty</p>
              ) : (
                col.items.map((m) => (
                  <div key={m.id} className="p-3 rounded bg-white/[0.02] border border-white/[0.06] space-y-2 hover:border-brand/40 transition">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-xs font-semibold text-[#f7f8f8]">{m.seeker_name ?? "Seeker"}</div>
                        <div className="text-[10px] text-[#8a8f98]">{m.contract_title ?? ""}</div>
                        {m.seeker_headline ? (
                          <div className="text-[10px] text-[#62666d] mt-0.5">{m.seeker_headline}</div>
                        ) : null}
                      </div>
                      <div className="text-right">
                        <div className={`font-mono font-bold text-sm ${m.tier === "A" ? "text-emerald-400" : m.tier === "B" ? "text-amber-400" : "text-[#8a8f98]"}`}>
                          {m.score}%
                        </div>
                        <TierBadge tier={m.tier} />
                      </div>
                    </div>
                    {m.hitl_required ? (
                      <div className="text-[10px] text-amber-400 py-1 px-1.5 rounded bg-amber-500/10">
                        awaiting human review
                      </div>
                    ) : null}
                    {!col.isTerminal ? (
                      <div className="flex space-x-2 pt-1">
                        {col.isEntry && col.key !== rejectKey ? (
                          <button
                            onClick={() => {
                              const next = getNextStageKey(col.key);
                              if (next) advance(m, next);
                            }}
                            className="flex-1 py-1.5 rounded bg-brand/20 hover:bg-brand/30 text-brand-light text-[10px] font-medium"
                          >
                            Approve
                          </button>
                        ) : null}
                        {col.isEntry && col.key !== rejectKey ? (
                          <button
                            onClick={() => advance(m, rejectKey)}
                            className="px-2 py-1.5 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 text-[10px]"
                          >
                            Reject
                          </button>
                        ) : null}
                        {!col.isEntry && col.key !== rejectKey ? (
                          <button
                            onClick={() => {
                              const next = getNextStageKey(col.key);
                              if (next) advance(m, next);
                            }}
                            className="flex-1 py-1.5 rounded bg-brand/20 hover:bg-brand/30 text-brand-light text-[10px] font-medium"
                          >
                            Next stage
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}