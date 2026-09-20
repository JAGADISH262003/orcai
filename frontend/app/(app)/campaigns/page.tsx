"use client";

import { useEffect, useState } from "react";

import { EmptyState, ErrorBanner, Loading, Modal } from "@/components/UI";
import { apiFetch } from "@/lib/client";
import type { Campaign, CampaignRecipient, Seeker } from "@/lib/types";

interface CampaignForm {
  name: string;
  description: string;
  channel: string;
  template_subject: string;
  template_body: string;
}

const EMPTY_FORM: CampaignForm = {
  name: "",
  description: "",
  channel: "email",
  template_subject: "",
  template_body: "",
};

const CHANNELS = ["email", "whatsapp", "telegram", "sms"];

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<CampaignForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [detailId, setDetailId] = useState<number | null>(null);
  const [recipients, setRecipients] = useState<CampaignRecipient[]>([]);
  const [recipientsLoading, setRecipientsLoading] = useState(false);

  const [addRecipientsOpen, setAddRecipientsOpen] = useState(false);
  const [seekers, setSeekers] = useState<Seeker[]>([]);
  const [selectedSeekerIds, setSelectedSeekerIds] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [addingRecipients, setAddingRecipients] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<Campaign[]>("/campaigns");
      setCampaigns(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function loadDetail(id: number) {
    setDetailId(id);
    setRecipientsLoading(true);
    try {
      const data = await apiFetch<CampaignRecipient[]>("/campaigns/" + id + "/recipients");
      setRecipients(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recipients");
    } finally {
      setRecipientsLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const created = await apiFetch<Campaign>("/campaigns", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setCampaigns((prev) => [created, ...prev]);
      setCreateOpen(false);
      setForm(EMPTY_FORM);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStart(id: number) {
    try {
      const updated = await apiFetch<Campaign>("/campaigns/" + id + "/start", { method: "POST" });
      setCampaigns((prev) => prev.map((c) => (c.id === id ? updated : c)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start campaign");
    }
  }

  async function handlePause(id: number) {
    try {
      const updated = await apiFetch<Campaign>("/campaigns/" + id + "/pause", { method: "POST" });
      setCampaigns((prev) => prev.map((c) => (c.id === id ? updated : c)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to pause campaign");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this campaign?")) return;
    try {
      await apiFetch("/campaigns/" + id, { method: "DELETE" });
      setCampaigns((prev) => prev.filter((c) => c.id !== id));
      if (detailId === id) setDetailId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete campaign");
    }
  }

  async function openAddRecipients() {
    setAddRecipientsOpen(true);
    setSearchQuery("");
    setSelectedSeekerIds(new Set());
    try {
      const data = await apiFetch<Seeker[]>("/seekers");
      setSeekers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load seekers");
    }
  }

  async function handleAddRecipients() {
    if (!detailId || selectedSeekerIds.size === 0) return;
    setAddingRecipients(true);
    try {
      await apiFetch("/campaigns/" + detailId + "/recipients/add", {
        method: "POST",
        body: JSON.stringify({ seeker_ids: Array.from(selectedSeekerIds) }),
      });
      setAddRecipientsOpen(false);
      loadDetail(detailId);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add recipients");
    } finally {
      setAddingRecipients(false);
    }
  }

  function toggleSeeker(id: number) {
    setSelectedSeekerIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function statusBadge(status: string) {
    const colors: Record<string, string> = {
      draft: "bg-[#8a8f98]/10 text-[#8a8f98] border-[#8a8f98]/20",
      active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      paused: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      completed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      cancelled: "bg-red-500/10 text-red-400 border-red-500/20",
      queued: "bg-[#8a8f98]/10 text-[#8a8f98] border-[#8a8f98]/20",
      sent: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      delivered: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      opened: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      replied: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      bounced: "bg-red-500/10 text-red-400 border-red-500/20",
      unsubscribed: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    return (
      <span className={"text-[10px] px-1.5 py-0.5 rounded border " + (colors[status] ?? "bg-white/10 text-[#8a8f98] border-white/10")}>
        {status}
      </span>
    );
  }

  const filteredSeekers = searchQuery
    ? seekers.filter(
        (s) =>
          (s.name && s.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (s.email && s.email.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : seekers;

  if (loading) return <Loading label="Loading campaigns..." />;
  if (error && campaigns.length === 0) return <ErrorBanner message={error} onRetry={load} />;

  const selected = detailId ? campaigns.find((c) => c.id === detailId) : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Sourcing Campaigns</h1>
          <p className="text-xs text-[#8a8f98] mt-1">Create automated outreach sequences to engage talent.</p>
        </div>
        <button
          onClick={() => { setForm(EMPTY_FORM); setSubmitError(null); setCreateOpen(true); }}
          className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
        >
          + New Campaign
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {campaigns.length === 0 ? (
        <EmptyState
          text="No campaigns yet. Create your first sourcing campaign to get started."
          action={
            <button
              onClick={() => { setForm(EMPTY_FORM); setSubmitError(null); setCreateOpen(true); }}
              className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium"
            >
              + New Campaign
            </button>
          }
        />
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <div key={c.id} className="linear-card p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <button
                    onClick={() => loadDetail(c.id)}
                    className="text-left w-full"
                  >
                    <h3 className="text-sm font-semibold text-[#f7f8f8] hover:text-[#5e6ad2] transition">{c.name}</h3>
                  </button>
                  <div className="flex items-center gap-2 mt-1">
                    {statusBadge(c.status)}
                    <span className="text-[10px] text-[#8a8f98] capitalize">{c.channel}</span>
                  </div>
                  {c.description && (
                    <p className="text-[11px] text-[#8a8f98] mt-1 truncate">{c.description}</p>
                  )}
                </div>
                <div className="flex items-center space-x-2 shrink-0">
                  {c.status === "draft" || c.status === "paused" ? (
                    <button
                      onClick={() => handleStart(c.id)}
                      className="px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-[10px] text-emerald-400"
                    >
                      Start
                    </button>
                  ) : null}
                  {c.status === "active" ? (
                    <button
                      onClick={() => handlePause(c.id)}
                      className="px-2 py-1 rounded bg-yellow-500/10 hover:bg-yellow-500/20 text-[10px] text-yellow-400"
                    >
                      Pause
                    </button>
                  ) : null}
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-[10px] text-red-400"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: "Target", value: c.target_count },
                  { label: "Sent", value: c.sent_count },
                  { label: "Opened", value: c.opened_count },
                  { label: "Replied", value: c.replied_count },
                ].map((stat) => (
                  <div key={stat.label} className="text-center p-2 rounded bg-white/[0.03]">
                    <div className="text-sm font-semibold text-[#f7f8f8]">{stat.value}</div>
                    <div className="text-[10px] text-[#8a8f98]">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="linear-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#f7f8f8]">{selected.name} - Recipients</h2>
              <p className="text-[10px] text-[#8a8f98] mt-0.5">
                {selected.sent_count} sent of {selected.target_count} target
                {selected.target_count > 0 && (
                  <span className="ml-2">
                    {" "}&middot; Open rate: {selected.sent_count > 0 ? Math.round((selected.opened_count / selected.sent_count) * 100) : 0}%
                    {" "}&middot; Reply rate: {selected.sent_count > 0 ? Math.round((selected.replied_count / selected.sent_count) * 100) : 0}%
                  </span>
                )}
              </p>
            </div>
            <div className="flex gap-2">
              {(selected.status === "draft" || selected.status === "paused") && (
                <button
                  onClick={openAddRecipients}
                  className="px-3 py-1.5 rounded bg-white/[0.06] hover:bg-white/[0.1] text-[11px] text-[#d0d6e0]"
                >
                  + Add Recipients
                </button>
              )}
              <button
                onClick={() => setDetailId(null)}
                className="text-[10px] text-[#8a8f98] hover:text-white px-2 py-1"
              >
                Close
              </button>
            </div>
          </div>

          {recipientsLoading ? (
            <Loading label="Loading recipients..." />
          ) : recipients.length === 0 ? (
            <p className="text-[11px] text-[#8a8f98]">No recipients added yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    <th className="text-left py-2 px-2 text-[10px] font-medium text-[#8a8f98]">Name</th>
                    <th className="text-left py-2 px-2 text-[10px] font-medium text-[#8a8f98]">Email</th>
                    <th className="text-left py-2 px-2 text-[10px] font-medium text-[#8a8f98]">Status</th>
                    <th className="text-left py-2 px-2 text-[10px] font-medium text-[#8a8f98]">Sent</th>
                    <th className="text-left py-2 px-2 text-[10px] font-medium text-[#8a8f98]">Opened</th>
                    <th className="text-left py-2 px-2 text-[10px] font-medium text-[#8a8f98]">Replied</th>
                  </tr>
                </thead>
                <tbody>
                  {recipients.map((r) => (
                    <tr key={r.id} className="border-b border-white/[0.04]">
                      <td className="py-2 px-2 text-[#d0d6e0]">{r.seeker_name ?? "-"}</td>
                      <td className="py-2 px-2 text-[#8a8f98]">{r.seeker_email ?? "-"}</td>
                      <td className="py-2 px-2">{statusBadge(r.status)}</td>
                      <td className="py-2 px-2 text-[#8a8f98]">{r.sent_at ? new Date(r.sent_at).toLocaleString() : "-"}</td>
                      <td className="py-2 px-2 text-[#8a8f98]">{r.opened_at ? new Date(r.opened_at).toLocaleString() : "-"}</td>
                      <td className="py-2 px-2 text-[#8a8f98]">{r.replied_at ? new Date(r.replied_at).toLocaleString() : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New Campaign">
        <form onSubmit={handleCreate} className="space-y-3">
          {submitError && (
            <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">{submitError}</div>
          )}
          <div className="space-y-3 text-xs">
            <input
              required
              placeholder="Campaign name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="linear-input w-full px-3 py-2"
            />
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Channel</label>
              <select
                className="linear-input w-full px-3 py-2"
                value={form.channel}
                onChange={(e) => setForm({ ...form, channel: e.target.value })}
              >
                {CHANNELS.map((ch) => (
                  <option key={ch} value={ch}>{ch}</option>
                ))}
              </select>
            </div>
            <input
              placeholder="Subject line (for email)"
              value={form.template_subject}
              onChange={(e) => setForm({ ...form, template_subject: e.target.value })}
              className="linear-input w-full px-3 py-2"
            />
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">
                Template Body - use {"{name}"}, {"{company}"}, {"{role}"} for personalization
              </label>
              <textarea
                rows={5}
                placeholder={"Hi {name},\n\nWe have an exciting opportunity that matches your profile..."}
                value={form.template_body}
                onChange={(e) => setForm({ ...form, template_body: e.target.value })}
                className="linear-input w-full px-3 py-2 text-xs"
              />
            </div>
            <textarea
              rows={2}
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="linear-input w-full px-3 py-2 text-xs"
            />
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
              {submitting ? "Creating..." : "Create Campaign"}
            </button>
          </div>
        </form>
      </Modal>

      <Modal open={addRecipientsOpen} onClose={() => setAddRecipientsOpen(false)} title="Add Recipients" wide>
        <div className="space-y-3">
          <input
            placeholder="Search by name or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="linear-input w-full px-3 py-2 text-xs"
          />
          <div className="max-h-64 overflow-y-auto space-y-1">
            {filteredSeekers.map((s) => (
              <label
                key={s.id}
                className="flex items-center space-x-3 p-2 rounded hover:bg-white/[0.04] cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedSeekerIds.has(s.id)}
                  onChange={() => toggleSeeker(s.id)}
                  className="w-4 h-4 rounded border-white/20 bg-white/[0.06] text-[#5e6ad2] focus:ring-[#5e6ad2] focus:ring-offset-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-[#f7f8f8]">{s.name ?? "Unnamed"}</div>
                  <div className="text-[10px] text-[#8a8f98] truncate">{s.email ?? "No email"}</div>
                </div>
              </label>
            ))}
            {filteredSeekers.length === 0 && (
              <p className="text-[11px] text-[#8a8f98] text-center py-4">No seekers found.</p>
            )}
          </div>
          <div className="flex justify-between items-center pt-3 border-t border-white/[0.08]">
            <span className="text-[10px] text-[#8a8f98]">{selectedSeekerIds.size} selected</span>
            <div className="flex space-x-2">
              <button
                onClick={() => setAddRecipientsOpen(false)}
                className="px-4 py-1.5 rounded bg-white/[0.08] text-white text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleAddRecipients}
                disabled={addingRecipients || selectedSeekerIds.size === 0}
                className="px-4 py-1.5 rounded bg-brand text-white text-xs disabled:opacity-50"
              >
                {addingRecipients ? "Adding..." : "Add " + selectedSeekerIds.size + " Recipients"}
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
