"use client";

import { useEffect, useState } from "react";

import { Badge, toneForStatus } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading, Modal } from "@/components/UI";
import { api, ApiError, pollJob } from "@/lib/client";
import type { Contract } from "@/lib/types";

export default function ContractsPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [rawText, setRawText] = useState("");
  const [clientName, setClientName] = useState("");
  const [posting, setPosting] = useState(false);
  const [postError, setPostError] = useState<string | null>(null);
  const [matching, setMatching] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setContracts(await api.contracts());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load contracts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submitContract(e: React.FormEvent) {
    e.preventDefault();
    setPostError(null);
    setPosting(true);
    try {
      const job = await api.createContract(rawText, clientName || undefined);
      const done = await pollJob(job.id);
      const contractId = (done.result?.contract_id as number | undefined) ?? null;
      setOpen(false);
      setRawText("");
      setClientName("");
      await load();
      if (contractId) {
        const m = await api.runMatching(contractId);
        await pollJob(m.id);
        await load();
      }
    } catch (err) {
      setPostError(err instanceof ApiError ? (err.message as string) : "Failed to post contract");
    } finally {
      setPosting(false);
    }
  }

  async function toggleStatus(c: Contract) {
    const next = c.status === "active" ? "closed" : "active";
    setContracts((prev) => prev.map((x) => (x.id === c.id ? { ...x, status: next } : x)));
  }

  async function remove(c: Contract) {
    if (!confirm(`Delete contract "${c.title ?? c.id}"? This removes its matches.`)) return;
    await fetch(`/api/contracts/${c.id}`, { method: "DELETE" });
    setContracts((prev) => prev.filter((x) => x.id !== c.id));
  }

  if (loading) return <Loading label="Loading contracts…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Employer Contracts & Requisitions</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Paste a client requirement — the extractor turns it into a structured, matchable requisition.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={async () => {
              setMatching(true);
              try {
                const job = await api.runMatching();
                await pollJob(job.id);
                await load();
              } catch (err) {
                setPostError(err instanceof ApiError ? (err.message as string) : "Matching failed");
              } finally {
                setMatching(false);
              }
            }}
            disabled={matching}
            className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50"
          >
            {matching ? "Matching…" : "Run matching engine"}
          </button>
          <button
            onClick={() => setOpen(true)}
            className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
          >
            + Post Employer Contract
          </button>
        </div>
      </div>

      {contracts.length === 0 ? (
        <EmptyState
          text="No contracts yet. Post an employer requisition to get started."
          action={
            <button
              onClick={() => setOpen(true)}
              className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium"
            >
              + Post Contract
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {contracts.map((c) => (
            <div key={c.id} className="linear-card p-5 space-y-3 bg-[#0f1011]">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-[#f7f8f8]">{c.title ?? "Untitled"}</h3>
                  <p className="text-[11px] text-[#8a8f98] mt-0.5">
                    {c.client_name ?? "Direct client"} · {c.location ?? "Location TBD"}
                    {c.is_remote ? " · Remote" : ""}
                  </p>
                </div>
                <Badge tone={toneForStatus(c.status)}>{c.status}</Badge>
              </div>

              <div className="flex flex-wrap gap-1">
                <span className="px-2 py-0.5 rounded bg-white/[0.06] text-[10px] font-mono text-[#d0d6e0]">
                  {c.currency} {c.rate_bill ?? "—"}/{c.rate_pay ?? "—"}
                </span>
                {c.experience_min != null ? (
                  <span className="px-2 py-0.5 rounded bg-white/[0.06] text-[10px] font-mono text-[#d0d6e0]">
                    {c.experience_min}+ yrs
                  </span>
                ) : null}
                {c.duration_months ? (
                  <span className="px-2 py-0.5 rounded bg-white/[0.06] text-[10px] font-mono text-[#d0d6e0]">
                    {c.duration_months} mo
                  </span>
                ) : null}
                <span className="px-2 py-0.5 rounded bg-white/[0.06] text-[10px] font-mono text-[#d0d6e0]">
                  {c.openings} slot{c.openings > 1 ? "s" : ""}
                </span>
              </div>

              {c.skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {c.skills.slice(0, 10).map((s) => (
                    <span
                      key={s}
                      className="px-1.5 py-0.5 rounded bg-brand/10 text-brand-light text-[10px]"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              ) : null}

              {c.ai_summary ? (
                <p className="text-[11px] text-[#8a8f98] leading-relaxed">{c.ai_summary}</p>
              ) : null}

              <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
                <div className="flex space-x-2">
                  <button
                    onClick={() => toggleStatus(c)}
                    className="px-2 py-1 rounded bg-white/[0.06] hover:bg-white/[0.1] text-[10px] text-[#d0d6e0]"
                  >
                    Mark {c.status === "active" ? "filled" : "active"}
                  </button>
                  <button
                    onClick={async () => {
                      const job = await api.runMatching(c.id);
                      await pollJob(job.id);
                      await load();
                    }}
                    className="px-2 py-1 rounded bg-brand/20 hover:bg-brand/30 text-[10px] text-brand-light"
                  >
                    Match seekers
                  </button>
                </div>
                <button
                  onClick={() => remove(c)}
                  className="px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-[10px] text-red-400"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Post Employer Contract (AI Extractor)">
        <form onSubmit={submitContract} className="space-y-4">
          {postError ? (
            <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">
              {postError}
            </div>
          ) : null}
          <div>
            <label className="text-[11px] text-[#8a8f98] font-medium">Client name (optional)</label>
            <input
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              className="linear-input w-full px-3 py-2 text-xs mt-1"
              placeholder="Wells Fargo"
            />
          </div>
          <div>
            <label className="text-[11px] text-[#8a8f98] font-medium">
              Raw contract / requisition text
            </label>
            <textarea
              required
              rows={6}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              className="linear-input w-full p-3 font-mono text-xs mt-1"
              placeholder={'Client: Wells Fargo. Role: Senior Java Fullstack Engineer. Requirements: Spring Boot, Angular, AWS. 8+ yrs exp. Rate: $85/hr bill rate. Immediate start.'}
            />
          </div>
          <div className="flex justify-end space-x-2 pt-3 border-t border-white/[0.08]">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="px-4 py-1.5 rounded bg-white/[0.08] text-white text-xs"
            >
              Cancel
            </button>
            <button
              disabled={posting}
              className="px-4 py-1.5 rounded bg-brand text-white text-xs disabled:opacity-50"
            >
              {posting ? "Parsing & matching…" : "Publish Contract & Match Seekers"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}