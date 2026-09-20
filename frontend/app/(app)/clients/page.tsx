"use client";

import { useEffect, useState } from "react";

import { EmptyState, ErrorBanner, Loading, Modal } from "@/components/UI";
import { api } from "@/lib/client";
import type { Client } from "@/lib/types";

interface ClientForm {
  name: string;
  industry: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  notes: string;
}

const EMPTY_FORM: ClientForm = {
  name: "",
  industry: "",
  contact_name: "",
  contact_email: "",
  contact_phone: "",
  notes: "",
};

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editClient, setEditClient] = useState<Client | null>(null);
  const [form, setForm] = useState<ClientForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setClients(await api.clients());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load clients");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openCreate() {
    setForm(EMPTY_FORM);
    setEditClient(null);
    setSubmitError(null);
    setCreateOpen(true);
  }

  function openEdit(c: Client) {
    setForm({
      name: c.name,
      industry: c.industry ?? "",
      contact_name: c.contact_name ?? "",
      contact_email: c.contact_email ?? "",
      contact_phone: c.contact_phone ?? "",
      notes: c.notes ?? "",
    });
    setEditClient(c);
    setSubmitError(null);
    setCreateOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const data = {
        name: form.name,
        industry: form.industry || undefined,
        contact_name: form.contact_name || undefined,
        contact_email: form.contact_email || undefined,
        contact_phone: form.contact_phone || undefined,
        notes: form.notes || undefined,
      };
      if (editClient) {
        const updated = await api.updateClient(editClient.id, data);
        setClients((prev) => prev.map((c) => (c.id === editClient.id ? { ...c, ...updated } : c)));
      } else {
        const created = await api.createClient(data);
        setClients((prev) => [created, ...prev]);
      }
      setCreateOpen(false);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Failed to save client");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(c: Client) {
    if (!confirm(`Delete client "${c.name}"?`)) return;
    try {
      await api.deleteClient(c.id);
      setClients((prev) => prev.filter((x) => x.id !== c.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete client");
    }
  }

  if (loading) return <Loading label="Loading clients…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Client Management</h1>
          <p className="text-xs text-[#8a8f98] mt-1">Manage your agency client accounts and contacts.</p>
        </div>
        <button
          onClick={openCreate}
          className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
        >
          + Add Client
        </button>
      </div>

      {clients.length === 0 ? (
        <EmptyState
          text="No clients yet. Add your first client to get started."
          action={
            <button
              onClick={openCreate}
              className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium"
            >
              + Add Client
            </button>
          }
        />
      ) : (
        <div className="space-y-3">
          {clients.map((c) => (
            <div key={c.id} className="linear-card p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <button
                    onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    className="text-left w-full"
                  >
                    <h3 className="text-sm font-semibold text-[#f7f8f8] hover:text-[#5e6ad2] transition">{c.name}</h3>
                  </button>
                  {c.industry && (
                    <p className="text-[11px] text-[#8a8f98] mt-0.5">{c.industry}</p>
                  )}
                </div>
                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={() => openEdit(c)}
                    className="px-2 py-1 rounded bg-white/[0.06] hover:bg-white/[0.1] text-[10px] text-[#d0d6e0]"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(c)}
                    className="px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-[10px] text-red-400"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[#8a8f98]">
                {c.contact_name && <span>Contact: <span className="text-[#d0d6e0]">{c.contact_name}</span></span>}
                {c.contact_email && <span>Email: <span className="text-[#d0d6e0]">{c.contact_email}</span></span>}
                {c.contact_phone && <span>Phone: <span className="text-[#d0d6e0]">{c.contact_phone}</span></span>}
              </div>

              {expandedId === c.id && (
                <div className="pt-2 border-t border-white/[0.06] space-y-2">
                  {c.notes && (
                    <p className="text-[11px] text-[#d0d6e0]">{c.notes}</p>
                  )}
                  <p className="text-[10px] text-[#62666d] font-mono">
                    Added: {new Date(c.created_at).toLocaleDateString()} · ID: {c.id}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title={editClient ? "Edit Client" : "Add Client"}
      >
        <form onSubmit={handleSubmit} className="space-y-3">
          {submitError && (
            <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">{submitError}</div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <input
              required
              placeholder="Client name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="linear-input px-3 py-2"
            />
            <input
              placeholder="Industry"
              value={form.industry}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
              className="linear-input px-3 py-2"
            />
            <input
              placeholder="Contact name"
              value={form.contact_name}
              onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
              className="linear-input px-3 py-2"
            />
            <input
              type="email"
              placeholder="Contact email"
              value={form.contact_email}
              onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
              className="linear-input px-3 py-2"
            />
            <input
              placeholder="Contact phone"
              value={form.contact_phone}
              onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
              className="linear-input px-3 py-2"
            />
            <div className="sm:col-span-2">
              <textarea
                rows={3}
                placeholder="Notes"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                className="linear-input w-full px-3 py-2 text-xs"
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
              {submitting ? "Saving…" : editClient ? "Update Client" : "Add Client"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
