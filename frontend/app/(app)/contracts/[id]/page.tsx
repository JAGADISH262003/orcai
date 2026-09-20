"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";

import { Badge, TierBadge, toneForStatus } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api, apiFetch, ApiError } from "@/lib/client";
import type { Contract, Match } from "@/lib/types";

const STATUS_FLOW: Record<string, string[]> = {
  draft: ["active"],
  active: ["paused", "closed"],
  paused: ["active", "closed"],
  closed: ["active"],
};

export default function ContractDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [contract, setContract] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const [matches, setMatches] = useState<Match[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, m] = await Promise.all([
        api.contract(id),
        api.matches(`?contract_id=${id}`),
      ]);
      setContract(c);
      setMatches(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load contract");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) load();
  }, [id, load]);

  function startEdit() {
    if (!contract) return;
    setEditForm({
      title: contract.title ?? "",
      location: contract.location ?? "",
      is_remote: contract.is_remote ? "true" : "false",
      duration_months: contract.duration_months != null ? String(contract.duration_months) : "",
      rate_bill: contract.rate_bill != null ? String(contract.rate_bill) : "",
      rate_pay: contract.rate_pay != null ? String(contract.rate_pay) : "",
      currency: contract.currency,
      experience_min: contract.experience_min != null ? String(contract.experience_min) : "",
      openings: String(contract.openings),
      start_by: contract.start_by ?? "",
      skills: (contract.skills ?? []).join(", "),
      summary: contract.ai_summary ?? "",
    });
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      const data: Record<string, unknown> = {};
      if (editForm.title) data.title = editForm.title;
      data.location = editForm.location || null;
      data.is_remote = editForm.is_remote === "true";
      data.duration_months = editForm.duration_months ? parseInt(editForm.duration_months) : null;
      data.rate_bill = editForm.rate_bill ? parseFloat(editForm.rate_bill) : null;
      data.rate_pay = editForm.rate_pay ? parseFloat(editForm.rate_pay) : null;
      data.currency = editForm.currency || "USD";
      data.experience_min = editForm.experience_min ? parseInt(editForm.experience_min) : null;
      data.openings = parseInt(editForm.openings) || 1;
      data.start_by = editForm.start_by || null;
      data.skills = editForm.skills.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
      data.ai_summary = editForm.summary || null;
      const updated = await api.updateContract(id, data);
      setContract(updated);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(status: string) {
    try {
      const updated = await api.setContractStatus(id, status);
      setContract(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    }
  }

  if (loading) return <Loading label="Loading contract…" />;
  if (error && !contract) return <ErrorBanner message={error} onRetry={load} />;
  if (!contract) return <EmptyState text="Contract not found" />;

  const nextStatuses = STATUS_FLOW[contract.status] ?? [];

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} />}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="text-[#8a8f98] hover:text-white text-xs">
            ← Back
          </button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">{contract.title ?? "Untitled Contract"}</h1>
            <p className="text-xs text-[#8a8f98] mt-1">
              {contract.client_name ?? "Direct client"} · {contract.location ?? "Location TBD"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={toneForStatus(contract.status)}>{contract.status}</Badge>
          {contract.parse_method && (
            <Badge tone="slate" mono>{contract.parse_method}</Badge>
          )}
          <button
            onClick={startEdit}
            className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
          >
            Edit Contract
          </button>
        </div>
      </div>

      {/* Status Actions */}
      {nextStatuses.length > 0 && (
        <div className="flex gap-2">
          {nextStatuses.map((s) => (
            <button
              key={s}
              onClick={() => changeStatus(s)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                s === "closed"
                  ? "bg-red-500/10 text-red-400 hover:bg-red-500/20"
                  : s === "active"
                    ? "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                    : "bg-white/[0.06] text-[#d0d6e0] hover:bg-white/[0.1]"
              }`}
            >
              Mark as {s}
            </button>
          ))}
        </div>
      )}

      {/* Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 linear-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Details</h2>
          {editing ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Title</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Location</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.location} onChange={(e) => setEditForm({ ...editForm, location: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Remote</label>
                <select className="linear-input w-full px-3 py-1.5" value={editForm.is_remote} onChange={(e) => setEditForm({ ...editForm, is_remote: e.target.value })}>
                  <option value="false">No</option>
                  <option value="true">Yes</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Duration (months)</label>
                <input className="linear-input w-full px-3 py-1.5" type="number" value={editForm.duration_months} onChange={(e) => setEditForm({ ...editForm, duration_months: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Currency</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.currency} onChange={(e) => setEditForm({ ...editForm, currency: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Bill Rate</label>
                <input className="linear-input w-full px-3 py-1.5" type="number" step="0.5" value={editForm.rate_bill} onChange={(e) => setEditForm({ ...editForm, rate_bill: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Pay Rate</label>
                <input className="linear-input w-full px-3 py-1.5" type="number" step="0.5" value={editForm.rate_pay} onChange={(e) => setEditForm({ ...editForm, rate_pay: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Min Experience (yrs)</label>
                <input className="linear-input w-full px-3 py-1.5" type="number" value={editForm.experience_min} onChange={(e) => setEditForm({ ...editForm, experience_min: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Openings</label>
                <input className="linear-input w-full px-3 py-1.5" type="number" value={editForm.openings} onChange={(e) => setEditForm({ ...editForm, openings: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Start By</label>
                <input className="linear-input w-full px-3 py-1.5" type="date" value={editForm.start_by} onChange={(e) => setEditForm({ ...editForm, start_by: e.target.value })} />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Skills (comma separated)</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.skills} onChange={(e) => setEditForm({ ...editForm, skills: e.target.value })} />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Summary</label>
                <textarea className="linear-input w-full px-3 py-1.5" rows={3} value={editForm.summary} onChange={(e) => setEditForm({ ...editForm, summary: e.target.value })} />
              </div>
              <div className="sm:col-span-2 flex justify-end gap-2 pt-2 border-t border-white/[0.06]">
                <button onClick={() => setEditing(false)} className="px-3 py-1.5 rounded bg-white/[0.08] text-white text-xs">Cancel</button>
                <button onClick={saveEdit} disabled={saving} className="px-3 py-1.5 rounded bg-brand text-white text-xs disabled:opacity-50">
                  {saving ? "Saving…" : "Save Changes"}
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-3 gap-x-6 text-xs">
              <div><span className="text-[#8a8f98]">Client: </span><span className="text-[#d0d6e0]">{contract.client_name ?? "Direct"}</span></div>
              <div><span className="text-[#8a8f98]">Status: </span><Badge tone={toneForStatus(contract.status)}>{contract.status}</Badge></div>
              <div><span className="text-[#8a8f98]">Location: </span><span className="text-[#d0d6e0]">{contract.location ?? "—"}</span></div>
              <div><span className="text-[#8a8f98]">Remote: </span><span className="text-[#d0d6e0]">{contract.is_remote ? "Yes" : "No"}</span></div>
              <div><span className="text-[#8a8f98]">Duration: </span><span className="text-[#d0d6e0]">{contract.duration_months != null ? `${contract.duration_months} months` : "—"}</span></div>
              <div><span className="text-[#8a8f98]">Currency: </span><span className="text-[#d0d6e0] font-mono">{contract.currency}</span></div>
              <div><span className="text-[#8a8f98]">Bill Rate: </span><span className="text-[#d0d6e0] font-mono">{contract.rate_bill != null ? `${contract.currency} ${contract.rate_bill}/hr` : "—"}</span></div>
              <div><span className="text-[#8a8f98]">Pay Rate: </span><span className="text-[#d0d6e0] font-mono">{contract.rate_pay != null ? `${contract.currency} ${contract.rate_pay}/hr` : "—"}</span></div>
              <div><span className="text-[#8a8f98]">Min Experience: </span><span className="text-[#d0d6e0]">{contract.experience_min != null ? `${contract.experience_min}+ years` : "—"}</span></div>
              <div><span className="text-[#8a8f98]">Openings: </span><span className="text-[#d0d6e0]">{contract.openings}</span></div>
              <div><span className="text-[#8a8f98]">Start By: </span><span className="text-[#d0d6e0]">{contract.start_by ?? "—"}</span></div>
              {contract.ai_summary && (
                <div className="sm:col-span-2 pt-2 border-t border-white/[0.06]">
                  <span className="text-[#8a8f98] block mb-1">AI Summary</span>
                  <p className="text-[#d0d6e0] leading-relaxed">{contract.ai_summary}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Skills Sidebar */}
        <div className="linear-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Required Skills</h2>
          {contract.skills.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {contract.skills.map((s) => (
                <span key={s} className="px-2 py-0.5 rounded bg-brand/10 text-brand-light text-[10px]">{s}</span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[#62666d]">No skills specified</p>
          )}
          <div className="pt-3 border-t border-white/[0.06] space-y-2 text-xs">
            <div><span className="text-[#8a8f98]">Created: </span><span className="text-[#d0d6e0]">{new Date(contract.created_at).toLocaleDateString()}</span></div>
            {contract.parse_method && (
              <div><span className="text-[#8a8f98]">Parsed via: </span><Badge tone="slate" mono>{contract.parse_method}</Badge></div>
            )}
          </div>
        </div>
      </div>

      {/* Matches */}
      <div className="linear-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">
          Matches <span className="text-[#8a8f98] font-normal">({matches.length})</span>
        </h2>
        {matches.length === 0 ? (
          <EmptyState text="No matches for this contract yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="text-left text-[10px] text-[#8a8f98] border-b border-white/[0.06]">
                <tr>
                  <th className="px-3 py-2 font-medium">Seeker</th>
                  <th className="px-3 py-2 font-medium">Score</th>
                  <th className="px-3 py-2 font-medium">Tier</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {matches.map((m) => (
                  <tr
                    key={m.id}
                    className="hover:bg-white/[0.02] cursor-pointer"
                    onClick={() => router.push(`/matches/${m.id}`)}
                  >
                    <td className="px-3 py-2 text-[#f7f8f8]">{m.seeker_name ?? `Seeker #${m.seeker_id}`}</td>
                    <td className="px-3 py-2 font-mono text-[#d0d6e0]">{m.score}%</td>
                    <td className="px-3 py-2"><TierBadge tier={m.tier} /></td>
                    <td className="px-3 py-2"><Badge tone={toneForStatus(m.status)}>{m.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
