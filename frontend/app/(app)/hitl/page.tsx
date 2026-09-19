"use client";

import { useEffect, useState } from "react";

import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type { Match } from "@/lib/types";

export default function HitlPage() {
  const [queue, setQueue] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<number, string>>({});

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setQueue(await api.hitlQueue());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load HITL queue");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(m: Match, decision: "approve" | "reject") {
    await api.reviewHitl(m.id, decision, notes[m.id]);
    setQueue((prev) => prev.filter((x) => x.id !== m.id));
  }

  if (loading) return <Loading label="Loading HITL queue…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">HITL Confidence Gate</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Review uncertain AI match scores before employer submissions.
          </p>
        </div>
        <span className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 text-xs font-mono font-bold">
          {queue.length} awaiting review
        </span>
      </div>

      {queue.length === 0 ? (
        <EmptyState text="Queue is clear. Great work — no ambiguous matches pending human review." />
      ) : (
        <div className="space-y-4">
          {queue.map((m) => (
            <div key={m.id} className="linear-card p-5 space-y-4 border-l-4 border-amber-500">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-full bg-amber-500/15 flex items-center justify-center font-bold text-amber-400">
                    {(m.seeker_name ?? "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[#f7f8f8]">{m.seeker_name}</h3>
                    <p className="text-xs text-[#8a8f98]">
                      Contract: {m.contract_title} · {m.seeker_headline ?? ""}
                    </p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 text-xs font-mono font-bold self-start">
                  AI Score: {m.score}% (Tier {m.tier})
                </span>
              </div>

              {m.rationale ? (
                <div className="p-3 rounded bg-black/40 border border-white/[0.06] text-xs space-y-1">
                  <p className="font-semibold text-amber-300">AI Uncertainty Rationale:</p>
                  <p className="text-[#d0d6e0]">{m.rationale}</p>
                </div>
              ) : null}

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 border-t border-white/[0.06]">
                <input
                  value={notes[m.id] ?? ""}
                  onChange={(e) => setNotes((prev) => ({ ...prev, [m.id]: e.target.value }))}
                  placeholder="Add recruiter review rationale…"
                  className="linear-input text-xs px-3 py-1.5 w-full sm:w-96"
                />
                <div className="flex space-x-2 w-full sm:w-auto">
                  <button
                    onClick={() => decide(m, "reject")}
                    className="px-4 py-1.5 rounded bg-red-500/10 text-red-400 text-xs font-medium transition hover:bg-red-500/20"
                  >
                    Reject Seeker
                  </button>
                  <button
                    onClick={() => decide(m, "approve")}
                    className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition"
                  >
                    Approve Seeker
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}