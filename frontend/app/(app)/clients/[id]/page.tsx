"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ErrorBanner, Loading } from "@/components/UI";
import { apiFetch } from "@/lib/client";
import { api } from "@/lib/client";
import type { Client } from "@/lib/types";

interface PortalSession {
  id: number;
  client_id: number;
  token_hash: string;
  expires_at: string;
  is_active: boolean;
  last_accessed_at: string | null;
  created_at: string;
  client_name?: string | null;
  token?: string;
}

interface Feedback {
  id: number;
  client_id: number;
  match_id: number;
  rating: number;
  feedback_text: string | null;
  status: string;
  created_at: string;
  client_name?: string | null;
  match_seeker_name?: string | null;
  match_contract_title?: string | null;
}

export default function ClientDetailPage() {
  const params = useParams();
  const clientId = Number(params.id);

  const [client, setClient] = useState<Client | null>(null);
  const [sessions, setSessions] = useState<PortalSession[]>([]);
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [portalLink, setPortalLink] = useState<string | null>(null);
  const [expiryDays, setExpiryDays] = useState(7);
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState<"portal" | "feedback">("portal");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const clients = await api.clients();
      const found = clients.find((c) => c.id === clientId);
      if (!found) {
        setError("Client not found");
        return;
      }
      setClient(found);
      const sess = await apiFetch<PortalSession[]>("/client-portal/sessions?client_id=" + clientId);
      setSessions(sess);
      const fbs = await apiFetch<Feedback[]>("/client-portal/feedback?client_id=" + clientId);
      setFeedbacks(fbs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load client details");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (clientId) load();
  }, [clientId]);

  async function generatePortalLink() {
    setGenerating(true);
    try {
      const result = await apiFetch<PortalSession>(
        "/client-portal/sessions",
        {
          method: "POST",
          body: JSON.stringify({ client_id: clientId, expiry_days: expiryDays }),
        }
      );
      const link = window.location.origin + "/portal/" + result.token;
      setPortalLink(link);
      setSessions((prev) => [{ ...result, client_name: client?.name }, ...prev]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate portal link");
    } finally {
      setGenerating(false);
    }
  }

  async function copyLink() {
    if (!portalLink) return;
    await navigator.clipboard.writeText(portalLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function statusBadge(status: string) {
    const colors: Record<string, string> = {
      pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      reviewed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      accepted: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    return (
      <span className={"text-[10px] px-1.5 py-0.5 rounded border " + (colors[status] ?? "bg-white/10 text-[#8a8f98] border-white/10")}>
        {status}
      </span>
    );
  }

  function stars(rating: number) {
    return Array.from({ length: 5 }, (_, i) => (
      <span key={i} className={i < rating ? "text-yellow-400" : "text-[#62666d]"}>&#9733;</span>
    ));
  }

  if (loading) return <Loading label="Loading client details..." />;
  if (error && !client) return <ErrorBanner message={error} onRetry={load} />;
  if (!client) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">{client.name}</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            {client.industry && <span>{client.industry} · </span>}
            {client.contact_email && <span>{client.contact_email}</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setTab("portal")}
            className={"px-3 py-1.5 rounded text-xs font-medium transition " + (tab === "portal" ? "bg-[#5e6ad2] text-white" : "bg-white/[0.06] text-[#8a8f98] hover:text-[#d0d6e0]")}
          >
            Portal Sessions
          </button>
          <button
            onClick={() => setTab("feedback")}
            className={"px-3 py-1.5 rounded text-xs font-medium transition " + (tab === "feedback" ? "bg-[#5e6ad2] text-white" : "bg-white/[0.06] text-[#8a8f98] hover:text-[#d0d6e0]")}
          >
            Feedback ({feedbacks.length})
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {tab === "portal" && (
        <div className="space-y-4">
          <div className="linear-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[#f7f8f8]">Generate Portal Link</h2>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <label className="text-[11px] text-[#8a8f98]">Expiry (days):</label>
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={expiryDays}
                  onChange={(e) => setExpiryDays(Number(e.target.value))}
                  className="linear-input px-2 py-1 text-xs w-16"
                />
              </div>
              <button
                onClick={generatePortalLink}
                disabled={generating}
                className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow disabled:opacity-50"
              >
                {generating ? "Generating..." : "Generate Portal Link"}
              </button>
            </div>
            {portalLink && (
              <div className="flex items-center gap-2 p-2.5 rounded bg-white/[0.04] border border-white/[0.06]">
                <code className="text-[11px] text-[#d0d6e0] flex-1 truncate">{portalLink}</code>
                <button
                  onClick={copyLink}
                  className="px-2 py-1 rounded bg-white/[0.08] hover:bg-white/[0.12] text-[10px] text-[#8a8f98] shrink-0"
                >
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            )}
          </div>

          <div className="linear-card p-4 space-y-3">
            <h2 className="text-sm font-semibold text-[#f7f8f8]">Portal Sessions</h2>
            {sessions.length === 0 ? (
              <p className="text-[11px] text-[#8a8f98]">No portal sessions yet.</p>
            ) : (
              <div className="space-y-2">
                {sessions.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-2.5 rounded bg-white/[0.04] border border-white/[0.06]">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={"text-[10px] px-1.5 py-0.5 rounded " + (s.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400")}>
                          {s.is_active ? "Active" : "Inactive"}
                        </span>
                        <span className="text-[10px] text-[#8a8f98]">
                          Expires: {new Date(s.expires_at).toLocaleDateString()}
                        </span>
                      </div>
                      {s.last_accessed_at && (
                        <p className="text-[10px] text-[#62666d]">
                          Last accessed: {new Date(s.last_accessed_at).toLocaleString()}
                        </p>
                      )}
                      <p className="text-[10px] text-[#62666d]">
                        Created: {new Date(s.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "feedback" && (
        <div className="linear-card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-[#f7f8f8]">Client Feedback</h2>
          {feedbacks.length === 0 ? (
            <p className="text-[11px] text-[#8a8f98]">No feedback submitted yet.</p>
          ) : (
            <div className="space-y-2">
              {feedbacks.map((fb) => (
                <div key={fb.id} className="p-3 rounded bg-white/[0.04] border border-white/[0.06] space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-[#f7f8f8]">
                        {fb.match_seeker_name ?? ("Match #" + fb.match_id)}
                      </span>
                      {fb.match_contract_title && (
                        <span className="text-[10px] text-[#8a8f98]">
                          for {fb.match_contract_title}
                        </span>
                      )}
                    </div>
                    {statusBadge(fb.status)}
                  </div>
                  <div className="flex items-center gap-1">
                    {stars(fb.rating)}
                    <span className="text-[10px] text-[#8a8f98] ml-1">({fb.rating}/5)</span>
                  </div>
                  {fb.feedback_text && (
                    <p className="text-[11px] text-[#d0d6e0]">{fb.feedback_text}</p>
                  )}
                  <p className="text-[10px] text-[#62666d]">
                    Submitted: {new Date(fb.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}