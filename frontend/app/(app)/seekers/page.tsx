"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading, Modal } from "@/components/UI";
import { api, ApiError, pollJob } from "@/lib/client";
import type { Seeker } from "@/lib/types";

export default function SeekersPage() {
  const [seekers, setSeekers] = useState<Seeker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [visa, setVisa] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [visaStatus, setVisaStatus] = useState("");
  const [fileKey, setFileKey] = useState(0);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    visa_status: "",
    location: "",
    headline: "",
    skills: "",
    experience_years: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      if (visa) params.set("visa", visa);
      const qs = params.toString();
      setSeekers(await api.seekers(qs ? `?${qs}` : ""));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load seekers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      const job = await api.uploadResume(file, visaStatus || undefined);
      await pollJob(job.id);
      setFileKey((k) => k + 1);
      setVisaStatus("");
      await load();
    } catch (err) {
      setUploadError(err instanceof ApiError ? (err.message as string) : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function submitManual(e: React.FormEvent) {
    e.preventDefault();
    const data = {
      name: form.name,
      email: form.email || undefined,
      phone: form.phone || undefined,
      visa_status: form.visa_status || undefined,
      location: form.location || undefined,
      headline: form.headline || undefined,
      skills: form.skills.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean),
      experience_years: form.experience_years ? parseFloat(form.experience_years) : undefined,
      summary: form.headline || undefined,
    };
    try {
      const created = await api.createSeeker(data);
      setSeekers((prev) => [created, ...prev]);
      setManualOpen(false);
      setForm({
        name: "",
        email: "",
        phone: "",
        visa_status: "",
        location: "",
        headline: "",
        skills: "",
        experience_years: "",
      });
    } catch (err) {
      setUploadError(err instanceof ApiError ? (err.message as string) : "Failed to add seeker");
    }
  }

  if (loading) return <Loading label="Loading talent pool…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Talent Pool · Verified Seekers</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Inbound, imported, and manually added employment seekers — deduplicated per agency.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setManualOpen(true)}
            className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition"
          >
            + Add manually
          </button>
          <label className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow cursor-pointer">
            {uploading ? "Uploading…" : "⤒ Upload resume(s)"}
            <input
              key={fileKey}
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(f);
                e.target.value = "";
              }}
            />
          </label>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!e.target.value) load();
          }}
          onKeyDown={(e) => e.key === "Enter" && load()}
          placeholder="Search by name, headline, email…"
          className="linear-input px-3 py-1.5 text-xs w-72"
        />
        <select value={visa} onChange={(e) => { setVisa(e.target.value); if (e.target.value) load(); }} className="linear-input px-3 py-1.5 text-xs">
          <option value="">All visas</option>
          {["H1B", "OPT", "GC EAD", "L1", "TN", "Citizen"].map((v) => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>
        <button onClick={load} className="px-3 py-1.5 rounded bg-white/[0.06] hover:bg-white/[0.1] text-xs text-[#d0d6e0]">
          Search
        </button>
      </div>

      {uploadError ? (
        <div className="p-3 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">{uploadError}</div>
      ) : null}

      {seekers.length === 0 ? (
        <EmptyState
          text="No seekers yet. Upload resumes or add a candidate manually."
          action={
            <label className="inline-block px-3 py-1.5 rounded bg-brand text-white text-xs font-medium cursor-pointer">
              Upload first resume
              <input
                type="file"
                accept=".pdf,.docx,.doc,.txt"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onUpload(f);
                }}
              />
            </label>
          }
        />
      ) : (
        <div className="overflow-x-auto linear-card">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
                <th className="py-2.5 px-3">Seeker</th>
                <th className="py-2.5 px-3">Visa</th>
                <th className="py-2.5 px-3">Exp</th>
                <th className="py-2.5 px-3">Skills</th>
                <th className="py-2.5 px-3">Source</th>
                <th className="py-2.5 px-3">Verified</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
              {seekers.map((s) => (
                <tr key={s.id} className="hover:bg-white/[0.02]">
                  <td className="py-3 px-3">
                    <div className="font-medium text-[#f7f8f8]">{s.name ?? "Unnamed candidate"}</div>
                    <div className="text-[10px] text-[#8a8f98]">{s.headline ?? s.email ?? "—"}</div>
                  </td>
                  <td className="py-3 px-3">{s.visa_status ?? "—"}</td>
                  <td className="py-3 px-3 font-mono">{s.experience_years != null ? `${s.experience_years}y` : "—"}</td>
                  <td className="py-3 px-3">
                    <div className="flex flex-wrap gap-1 max-w-xs">
                      {(s.skills ?? []).slice(0, 5).map((sk) => (
                        <span key={sk} className="px-1.5 py-0.5 rounded bg-brand/10 text-brand-light text-[10px]">{sk}</span>
                      ))}
                      {(s.skills ?? []).length > 5 ? (
                        <span className="text-[10px] text-[#62666d]">+{(s.skills ?? []).length - 5}</span>
                      ) : null}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <Badge tone={s.source === "inbound" ? "brand" : s.source === "import" ? "blue" : "slate"}>
                      {s.source}
                    </Badge>
                  </td>
                  <td className="py-3 px-3">{s.is_verified ? <span className="text-emerald-400">✓</span> : <span className="text-[#62666d]">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={manualOpen} onClose={() => setManualOpen(false)} title="Add Seeker Manually">
        <form onSubmit={submitManual} className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <input required placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="linear-input px-3 py-2" />
          <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="linear-input px-3 py-2" />
          <input placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="linear-input px-3 py-2" />
          <input placeholder="Visa status (H1B/OPT/GC…)" value={form.visa_status} onChange={(e) => setForm({ ...form, visa_status: e.target.value })} className="linear-input px-3 py-2" />
          <input placeholder="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className="linear-input px-3 py-2" />
          <input placeholder="Years experience" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: e.target.value })} className="linear-input px-3 py-2" />
          <input placeholder="Headline (e.g. Senior Java Architect)" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} className="linear-input px-3 py-2 sm:col-span-2" />
          <input placeholder="Skills, comma separated" value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} className="linear-input px-3 py-2 sm:col-span-2" />
          <div className="sm:col-span-2 flex justify-end space-x-2 pt-2 border-t border-white/[0.08]">
            <button type="button" onClick={() => setManualOpen(false)} className="px-4 py-1.5 rounded bg-white/[0.08] text-white text-xs">Cancel</button>
            <button className="px-4 py-1.5 rounded bg-brand text-white text-xs">Add Seeker</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}