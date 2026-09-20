"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";

import { Badge, TierBadge, toneForStatus } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api, apiFetch, ApiError } from "@/lib/client";
import type { Match, Seeker } from "@/lib/types";

interface Tag {
  id: number;
  agency_id: number;
  name: string;
  color: string;
}

interface Note {
  id: number;
  agency_id: number;
  user_id: number;
  entity_type: string;
  entity_id: number;
  content: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export default function SeekerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [seeker, setSeeker] = useState<Seeker | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const [tags, setTags] = useState<Tag[]>([]);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [newTagName, setNewTagName] = useState("");
  const [addingTag, setAddingTag] = useState(false);

  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  const [matches, setMatches] = useState<Match[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, seekerTags, n, m] = await Promise.all([
        api.seeker(id),
        api.seekerTags(id),
        api.notes("seeker", id),
        api.matches(`?seeker_id=${id}`),
      ]);
      setSeeker(s);
      setTags(seekerTags);
      setNotes(n);
      setMatches(m);
      const all = await api.tags();
      setAllTags(all);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load seeker");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) load();
  }, [id, load]);

  function startEdit() {
    if (!seeker) return;
    setEditForm({
      name: seeker.name ?? "",
      email: seeker.email ?? "",
      phone: seeker.phone ?? "",
      visa_status: seeker.visa_status ?? "",
      location: seeker.location ?? "",
      headline: seeker.headline ?? "",
      experience_years: seeker.experience_years != null ? String(seeker.experience_years) : "",
      summary: seeker.summary ?? "",
      education: seeker.education ?? "",
    });
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      const data: Record<string, unknown> = {};
      if (editForm.name) data.name = editForm.name;
      data.email = editForm.email || null;
      data.phone = editForm.phone || null;
      data.visa_status = editForm.visa_status || null;
      data.location = editForm.location || null;
      data.headline = editForm.headline || null;
      data.experience_years = editForm.experience_years ? parseFloat(editForm.experience_years) : null;
      data.summary = editForm.summary || null;
      data.education = editForm.education || null;
      const updated = await api.updateSeeker(id, data);
      setSeeker(updated);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleAttachTag(tagId: number) {
    try {
      await api.attachTag(id, tagId);
      const updated = await api.seekerTags(id);
      setTags(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to attach tag");
    }
  }

  async function handleDetachTag(tagId: number) {
    try {
      await api.detachTag(id, tagId);
      setTags((prev) => prev.filter((t) => t.id !== tagId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to detach tag");
    }
  }

  async function handleCreateTag() {
    if (!newTagName.trim()) return;
    setAddingTag(true);
    try {
      const tag = await api.createTag(newTagName.trim());
      setAllTags((prev) => [...prev, tag]);
      await api.attachTag(id, tag.id);
      setTags((prev) => [...prev, tag]);
      setNewTagName("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create tag");
    } finally {
      setAddingTag(false);
    }
  }

  async function handleAddNote() {
    if (!newNote.trim()) return;
    setAddingNote(true);
    try {
      const note = await api.createNote("seeker", id, newNote.trim());
      setNotes((prev) => [note, ...prev]);
      setNewNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add note");
    } finally {
      setAddingNote(false);
    }
  }

  async function handleDeleteNote(noteId: number) {
    try {
      await api.deleteNote(noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete note");
    }
  }

  if (loading) return <Loading label="Loading seeker profile…" />;
  if (error && !seeker) return <ErrorBanner message={error} onRetry={load} />;
  if (!seeker) return <EmptyState text="Seeker not found" />;

  const tagIds = new Set(tags.map((t) => t.id));
  const availableTags = allTags.filter((t) => !tagIds.has(t.id));

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
            <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">{seeker.name ?? "Unnamed Seeker"}</h1>
            <p className="text-xs text-[#8a8f98] mt-1">
              {seeker.headline ?? "No headline"} · {seeker.source}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={seeker.is_verified ? "emerald" : "slate"}>
            {seeker.is_verified ? "Verified" : "Unverified"}
          </Badge>
          <Badge tone={toneForStatus(seeker.is_active ? "active" : "closed")}>
            {seeker.is_active ? "Active" : "Inactive"}
          </Badge>
          <button
            onClick={startEdit}
            className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
          >
            Edit Profile
          </button>
        </div>
      </div>

      {/* Profile Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 linear-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Profile</h2>
          {editing ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Name</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Email</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Phone</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Visa Status</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.visa_status} onChange={(e) => setEditForm({ ...editForm, visa_status: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Location</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.location} onChange={(e) => setEditForm({ ...editForm, location: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Headline</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.headline} onChange={(e) => setEditForm({ ...editForm, headline: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Experience (years)</label>
                <input className="linear-input w-full px-3 py-1.5" type="number" step="0.5" value={editForm.experience_years} onChange={(e) => setEditForm({ ...editForm, experience_years: e.target.value })} />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Education</label>
                <input className="linear-input w-full px-3 py-1.5" value={editForm.education} onChange={(e) => setEditForm({ ...editForm, education: e.target.value })} />
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
              <Field label="Email" value={seeker.email} />
              <Field label="Phone" value={seeker.phone} />
              <Field label="Visa Status" value={seeker.visa_status} />
              <Field label="Location" value={seeker.location} />
              <Field label="Headline" value={seeker.headline} />
              <Field label="Experience" value={seeker.experience_years != null ? `${seeker.experience_years} years` : null} />
              <Field label="Education" value={seeker.education} />
              <Field label="Source" value={seeker.source} />
              {seeker.resume_path && (
                <div className="sm:col-span-2">
                  <span className="text-[#8a8f98]">Resume: </span>
                  <a
                    href={`/api/seekers/${seeker.id}/resume`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-light hover:underline"
                  >
                    Download
                  </a>
                </div>
              )}
              {seeker.summary && (
                <div className="sm:col-span-2 pt-2 border-t border-white/[0.06]">
                  <span className="text-[#8a8f98] block mb-1">Summary</span>
                  <p className="text-[#d0d6e0] leading-relaxed">{seeker.summary}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Skills Sidebar */}
        <div className="linear-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Skills</h2>
          {seeker.skills.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {seeker.skills.map((s) => (
                <span key={s} className="px-2 py-0.5 rounded bg-brand/10 text-brand-light text-[10px]">{s}</span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[#62666d]">No skills listed</p>
          )}
        </div>
      </div>

      {/* Tags */}
      <div className="linear-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Tags</h2>
        <div className="flex flex-wrap gap-2 items-center">
          {tags.map((t) => (
            <span
              key={t.id}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-medium"
              style={{ backgroundColor: `${t.color}15`, color: t.color, borderColor: `${t.color}30` }}
            >
              {t.name}
              <button onClick={() => handleDetachTag(t.id)} className="ml-0.5 opacity-60 hover:opacity-100">✕</button>
            </span>
          ))}
          {availableTags.length > 0 && (
            <select
              className="linear-input px-2 py-1 text-[10px]"
              value=""
              onChange={(e) => {
                const tagId = Number(e.target.value);
                if (tagId) handleAttachTag(tagId);
              }}
            >
              <option value="">+ Add tag…</option>
              {availableTags.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          )}
          <div className="flex items-center gap-1">
            <input
              className="linear-input px-2 py-1 text-[10px] w-28"
              placeholder="New tag…"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreateTag()}
            />
            <button
              onClick={handleCreateTag}
              disabled={addingTag || !newTagName.trim()}
              className="px-2 py-1 rounded bg-brand/20 text-brand-light text-[10px] disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="linear-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Notes</h2>
        <div className="flex gap-2">
          <input
            className="linear-input flex-1 px-3 py-1.5 text-xs"
            placeholder="Add a note…"
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddNote()}
          />
          <button
            onClick={handleAddNote}
            disabled={addingNote || !newNote.trim()}
            className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3 py-1.5 rounded-md transition disabled:opacity-50"
          >
            {addingNote ? "Adding…" : "Add Note"}
          </button>
        </div>
        {notes.length === 0 ? (
          <p className="text-xs text-[#62666d] py-4 text-center">No notes yet</p>
        ) : (
          <div className="space-y-2">
            {notes.map((n) => (
              <div key={n.id} className="flex items-start justify-between gap-3 p-3 rounded bg-black/30 border border-white/[0.06] text-xs">
                <div className="flex-1 min-w-0">
                  <p className="text-[#d0d6e0] whitespace-pre-wrap">{n.content}</p>
                  <p className="text-[10px] text-[#62666d] mt-1">
                    {new Date(n.created_at).toLocaleString()}
                    {n.is_pinned ? " · Pinned" : ""}
                  </p>
                </div>
                <button onClick={() => handleDeleteNote(n.id)} className="text-[#62666d] hover:text-red-400 text-[10px] shrink-0">Delete</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Matches */}
      <div className="linear-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">
          Matches <span className="text-[#8a8f98] font-normal">({matches.length})</span>
        </h2>
        {matches.length === 0 ? (
          <EmptyState text="No matches for this seeker yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="text-left text-[10px] text-[#8a8f98] border-b border-white/[0.06]">
                <tr>
                  <th className="px-3 py-2 font-medium">Contract</th>
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
                    <td className="px-3 py-2 text-[#f7f8f8]">{m.contract_title ?? `Contract #${m.contract_id}`}</td>
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

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <span className="text-[#8a8f98]">{label}: </span>
      <span className="text-[#d0d6e0]">{value || "—"}</span>
    </div>
  );
}
