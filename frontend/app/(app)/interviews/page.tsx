"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading, Modal } from "@/components/UI";
import { api } from "@/lib/client";
import type { Contract, Interview, Seeker } from "@/lib/types";

const TYPES = ["video", "phone", "onsite", "panel"] as const;

function statusTone(s: string): string {
  switch (s) {
    case "scheduled": return "blue";
    case "completed": return "emerald";
    case "cancelled": return "red";
    case "no_show": return "amber";
    default: return "slate";
  }
}

function statusLabel(s: string): string {
  return s.replace(/_/g, " ");
}

interface InterviewForm {
  contract_id: string;
  seeker_id: string;
  scheduled_at: string;
  interview_type: string;
  interviewer_name: string;
  interviewer_email: string;
  location: string;
  meeting_link: string;
}

const EMPTY_FORM: InterviewForm = {
  contract_id: "",
  seeker_id: "",
  scheduled_at: "",
  interview_type: "video",
  interviewer_name: "",
  interviewer_email: "",
  location: "",
  meeting_link: "",
};

export default function InterviewsPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [seekers, setSeekers] = useState<Seeker[]>([]);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterSeeker, setFilterSeeker] = useState("");
  const [filterContract, setFilterContract] = useState("");
  const [seekersMap, setSeekersMap] = useState<Record<number, string>>({});
  const [contractsMap, setContractsMap] = useState<Record<number, string>>({});
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<InterviewForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editFields, setEditFields] = useState<{ feedback: string; outcome: string; rating: string }>({ feedback: "", outcome: "", rating: "" });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      if (filterSeeker) params.set("seeker_id", filterSeeker);
      if (filterContract) params.set("contract_id", filterContract);
      const qs = params.toString();
      const [iv, co, se] = await Promise.all([
        api.interviews(qs ? `?${qs}` : ""),
        api.contracts(),
        api.seekers(),
      ]);
      setInterviews(iv);
      setContracts(co);
      setSeekers(se);
      const sMap: Record<number, string> = {};
      se.forEach((s) => { if (s.name) sMap[s.id] = s.name; });
      setSeekersMap(sMap);
      const cMap: Record<number, string> = {};
      co.forEach((c) => { if (c.title) cMap[c.id] = c.title; });
      setContractsMap(cMap);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load interviews");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const data: Record<string, unknown> = {
        contract_id: parseInt(form.contract_id),
        seeker_id: parseInt(form.seeker_id),
        scheduled_at: form.scheduled_at,
        interview_type: form.interview_type,
        interviewer_name: form.interviewer_name || null,
        interviewer_email: form.interviewer_email || null,
        location: form.location || null,
        meeting_link: form.meeting_link || null,
      };
      const created = await api.createInterview(data);
      setInterviews((prev) => [created, ...prev]);
      setCreateOpen(false);
      setForm(EMPTY_FORM);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Failed to create interview");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(id: number) {
    try {
      const updated = await api.updateInterview(id, {
        feedback: editFields.feedback || null,
        outcome: editFields.outcome || null,
        rating: editFields.rating ? parseInt(editFields.rating) : null,
      });
      setInterviews((prev) => prev.map((iv) => (iv.id === id ? { ...iv, ...updated } : iv)));
      setEditingId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update interview");
    }
  }

  async function handleCancel(id: number) {
    if (!confirm("Cancel this interview?")) return;
    try {
      const updated = await api.cancelInterview(id);
      setInterviews((prev) => prev.map((iv) => (iv.id === id ? { ...iv, ...updated } : iv)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to cancel interview");
    }
  }

  const sorted = [...interviews].sort((a, b) => {
    if (a.status === "scheduled" && b.status !== "scheduled") return -1;
    if (a.status !== "scheduled" && b.status === "scheduled") return 1;
    const da = a.scheduled_at ? new Date(a.scheduled_at).getTime() : 0;
    const db = b.scheduled_at ? new Date(b.scheduled_at).getTime() : 0;
    return db - da;
  });

  if (loading) return <Loading label="Loading interviews…" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Interview Scheduler</h1>
          <p className="text-xs text-[#8a8f98] mt-1">Schedule, manage, and track candidate interviews.</p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
        >
          + Schedule Interview
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="flex flex-wrap gap-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="linear-input px-3 py-1.5 text-xs"
        >
          <option value="">All statuses</option>
          <option value="scheduled">Scheduled</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
          <option value="no_show">No Show</option>
        </select>
        <select
          value={filterSeeker}
          onChange={(e) => setFilterSeeker(e.target.value)}
          className="linear-input px-3 py-1.5 text-xs"
        >
          <option value="">All seekers</option>
          {seekers.map((s) => (
            <option key={s.id} value={s.id}>{s.name ?? `Seeker #${s.id}`}</option>
          ))}
        </select>
        <select
          value={filterContract}
          onChange={(e) => setFilterContract(e.target.value)}
          className="linear-input px-3 py-1.5 text-xs"
        >
          <option value="">All contracts</option>
          {contracts.map((c) => (
            <option key={c.id} value={c.id}>{c.title ?? `Contract #${c.id}`}</option>
          ))}
        </select>
        <button
          onClick={load}
          className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition"
        >
          Filter
        </button>
      </div>

      {sorted.length === 0 ? (
        <EmptyState
          text="No interviews scheduled yet."
          action={
            <button
              onClick={() => setCreateOpen(true)}
              className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium"
            >
              + Schedule Interview
            </button>
          }
        />
      ) : (
        <div className="space-y-3">
          {sorted.map((iv) => (
            <div key={iv.id} className="linear-card p-4 space-y-3">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-full bg-white/[0.06] flex items-center justify-center font-bold text-[#d0d6e0] text-xs">
                    {(seekersMap[iv.seeker_id] ?? "?").split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[#f7f8f8]">{seekersMap[iv.seeker_id] ?? `Seeker #${iv.seeker_id}`}</h3>
                    <p className="text-[11px] text-[#8a8f98]">
                      {contractsMap[iv.contract_id] ?? `Contract #${iv.contract_id}`} · {iv.interview_type} · {iv.interviewer_name ?? "—"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge tone={statusTone(iv.status)}>{statusLabel(iv.status)}</Badge>
                  <span className="text-[10px] text-[#62666d] font-mono">
                    {iv.scheduled_at ? new Date(iv.scheduled_at).toLocaleString() : "—"}
                  </span>
                </div>
              </div>

              {(iv.location || iv.meeting_link) && (
                <p className="text-[11px] text-[#8a8f98]">
                  {iv.location && `Location: ${iv.location}`}
                  {iv.location && iv.meeting_link && " · "}
                  {iv.meeting_link && <a href={iv.meeting_link} target="_blank" rel="noopener noreferrer" className="text-[#5e6ad2] hover:underline">{iv.meeting_link}</a>}
                </p>
              )}

              {editingId === iv.id ? (
                <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div>
                      <label className="block text-[10px] text-[#8a8f98] mb-1">Outcome</label>
                      <input
                        className="linear-input w-full px-2 py-1 text-[11px]"
                        placeholder="hired / rejected / pending"
                        value={editFields.outcome}
                        onChange={(e) => setEditFields({ ...editFields, outcome: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-[#8a8f98] mb-1">Rating (1-5)</label>
                      <input
                        type="number"
                        min={1}
                        max={5}
                        className="linear-input w-full px-2 py-1 text-[11px]"
                        value={editFields.rating}
                        onChange={(e) => setEditFields({ ...editFields, rating: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-[#8a8f98] mb-1">Feedback</label>
                      <input
                        className="linear-input w-full px-2 py-1 text-[11px]"
                        placeholder="Interviewer feedback..."
                        value={editFields.feedback}
                        onChange={(e) => setEditFields({ ...editFields, feedback: e.target.value })}
                      />
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleUpdate(iv.id)}
                      className="px-3 py-1 rounded bg-brand text-white text-[11px] font-medium"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-3 py-1 rounded bg-white/[0.06] text-[#d0d6e0] text-[11px]"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
                  <div className="text-[11px] text-[#8a8f98] space-x-3">
                    {iv.outcome && <span>Outcome: <span className="text-[#d0d6e0]">{iv.outcome}</span></span>}
                    {iv.rating != null && <span>Rating: <span className="text-[#d0d6e0]">{iv.rating}/5</span></span>}
                    {iv.feedback && <span>Feedback: <span className="text-[#d0d6e0] truncate max-w-xs">{iv.feedback}</span></span>}
                  </div>
                  <div className="flex space-x-2">
                    {iv.status === "scheduled" && (
                      <>
                        <button
                          onClick={() => {
                            setEditingId(iv.id);
                            setEditFields({ feedback: iv.feedback ?? "", outcome: iv.outcome ?? "", rating: iv.rating != null ? String(iv.rating) : "" });
                          }}
                          className="px-2 py-1 rounded bg-white/[0.06] hover:bg-white/[0.1] text-[10px] text-[#d0d6e0]"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleCancel(iv.id)}
                          className="px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-[10px] text-red-400"
                        >
                          Cancel
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Schedule Interview" wide>
        <form onSubmit={handleCreate} className="space-y-4">
          {submitError && (
            <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">{submitError}</div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Contract</label>
              <select
                required
                className="linear-input w-full px-3 py-1.5 text-xs"
                value={form.contract_id}
                onChange={(e) => setForm({ ...form, contract_id: e.target.value })}
              >
                <option value="">Select contract</option>
                {contracts.map((c) => (
                  <option key={c.id} value={c.id}>{c.title ?? `Contract #${c.id}`}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Candidate</label>
              <select
                required
                className="linear-input w-full px-3 py-1.5 text-xs"
                value={form.seeker_id}
                onChange={(e) => setForm({ ...form, seeker_id: e.target.value })}
              >
                <option value="">Select candidate</option>
                {seekers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name ?? `Seeker #${s.id}`}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Date & Time</label>
              <input
                type="datetime-local"
                required
                className="linear-input w-full px-3 py-1.5 text-xs"
                value={form.scheduled_at}
                onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Type</label>
              <select
                className="linear-input w-full px-3 py-1.5 text-xs"
                value={form.interview_type}
                onChange={(e) => setForm({ ...form, interview_type: e.target.value })}
              >
                {TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Interviewer Name</label>
              <input
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="John Smith"
                value={form.interviewer_name}
                onChange={(e) => setForm({ ...form, interviewer_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Interviewer Email</label>
              <input
                type="email"
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="john@company.com"
                value={form.interviewer_email}
                onChange={(e) => setForm({ ...form, interviewer_email: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Location</label>
              <input
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="Office Room 3B"
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Meeting Link</label>
              <input
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="https://zoom.us/j/..."
                value={form.meeting_link}
                onChange={(e) => setForm({ ...form, meeting_link: e.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end space-x-2 pt-3 border-t border-white/[0.08]">
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              className="px-4 py-1.5 rounded bg-white/[0.08] text-white text-xs"
            >
              Cancel
            </button>
            <button
              disabled={submitting}
              className="px-4 py-1.5 rounded bg-brand text-white text-xs disabled:opacity-50"
            >
              {submitting ? "Scheduling…" : "Schedule Interview"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
