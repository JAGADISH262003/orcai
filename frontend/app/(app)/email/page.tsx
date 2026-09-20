"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, Loading, Modal, EmptyState } from "@/components/UI";
import { api } from "@/lib/client";

const TEMPLATES = [
  "None",
  "invite",
  "password_reset",
  "interview_scheduled",
  "offer_letter",
  "follow_up",
];

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-[#8a8f98]/20 text-[#8a8f98]",
  sent: "bg-blue-500/20 text-blue-300",
  delivered: "bg-emerald-500/20 text-emerald-300",
  opened: "bg-emerald-400/20 text-emerald-200",
  bounced: "bg-red-500/20 text-red-300",
  failed: "bg-red-500/20 text-red-300",
};

interface EmailHistoryEntry {
  id: number;
  to_email: string;
  subject: string;
  status: string;
  sent_at: string;
  template_name: string | null;
}

export default function EmailPage() {
  const [tab, setTab] = useState<"compose" | "history">("compose");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Compose state
  const [toEmail, setToEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [template, setTemplate] = useState("None");
  const [templateVars, setTemplateVars] = useState<Record<string, string>>({});
  const [entityType, setEntityType] = useState("");
  const [entityId, setEntityId] = useState("");
  const [sending, setSending] = useState(false);
  const [sendMsg, setSendMsg] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);

  // History state
  const [history, setHistory] = useState<EmailHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const LIMIT = 20;

  useEffect(() => {
    setLoading(false);
  }, []);

  useEffect(() => {
    if (tab === "history") loadHistory(true);
  }, [tab, statusFilter]);

  async function loadHistory(reset = false) {
    setHistoryLoading(true);
    try {
      const params: Record<string, unknown> = { limit: LIMIT, offset: reset ? 0 : offset };
      if (statusFilter) params.status = statusFilter;
      const data = await api.emailHistory(params);
      if (reset) {
        setHistory(data);
        setOffset(data.length);
      } else {
        setHistory((prev) => [...prev, ...data]);
        setOffset((prev) => prev + data.length);
      }
      setHasMore(data.length === LIMIT);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  }

  function handleTemplateChange(tpl: string) {
    setTemplate(tpl);
    if (tpl !== "None") {
      const vars: Record<string, string> = {};
      if (tpl === "invite") {
        vars["inviter_name"] = "";
        vars["agency_name"] = "";
        vars["portal_url"] = "";
      } else if (tpl === "password_reset") {
        vars["user_name"] = "";
        vars["reset_url"] = "";
      } else if (tpl === "interview_scheduled") {
        vars["candidate_name"] = "";
        vars["interview_date"] = "";
        vars["interview_time"] = "";
        vars["interview_link"] = "";
      } else if (tpl === "offer_letter") {
        vars["candidate_name"] = "";
        vars["position"] = "";
        vars["company_name"] = "";
        vars["start_date"] = "";
      } else if (tpl === "follow_up") {
        vars["recipient_name"] = "";
        vars["follow_up_context"] = "";
      }
      setTemplateVars(vars);
    } else {
      setTemplateVars({});
    }
  }

  async function handlePreview() {
    setPreviewLoading(true);
    try {
      const data = await api.emailPreview({
        subject,
        body_html: body,
        template_name: template !== "None" ? template : undefined,
        template_vars: Object.keys(templateVars).length > 0 ? templateVars : undefined,
      });
      setPreviewHtml(data.html ?? body);
      setPreviewOpen(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to preview");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleSend() {
    if (!toEmail || !subject || !body) {
      setError("To, subject, and body are required");
      return;
    }
    setSending(true);
    setError(null);
    setSendMsg(null);
    try {
      await api.emailSend({
        to_email: toEmail,
        subject,
        body_html: body,
        template_name: template !== "None" ? template : undefined,
        template_vars: Object.keys(templateVars).length > 0 ? templateVars : undefined,
        related_entity_type: entityType || undefined,
        related_entity_id: entityId ? Number(entityId) : undefined,
      });
      setSendMsg("Email queued for sending");
      setTimeout(() => setSendMsg(null), 3000);
      setToEmail("");
      setSubject("");
      setBody("");
      setTemplate("None");
      setTemplateVars({});
      setEntityType("");
      setEntityId("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send email");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Email</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Compose, send, and track emails to candidates and clients.</p>
      </div>

      <div className="flex gap-2 border-b border-white/[0.06] pb-2">
        {(["compose", "history"] as const).map((t) => (
          <button
            key={t}
            className={`px-3 py-1 text-xs font-medium rounded transition capitalize ${tab === t ? "bg-[#5e6ad2] text-white" : "text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-white/[0.04]"}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message={error} />}

      {sendMsg && (
        <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">{sendMsg}</div>
      )}

      {loading ? (
        <Loading label="Loading…" />
      ) : tab === "compose" ? (
        <div className="linear-card p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">To Email</label>
              <input
                type="email"
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="candidate@example.com"
                value={toEmail}
                onChange={(e) => setToEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Subject</label>
              <input
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="Interview scheduled"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Body</label>
            <textarea
              rows={8}
              className="linear-input w-full px-3 py-2 text-xs"
              placeholder="Write your email body here. Markdown formatting is supported."
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <p className="text-[10px] text-[#62666d] mt-1">Markdown is supported. HTML will be rendered for the recipient.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Template</label>
              <select
                className="linear-input w-full px-3 py-1.5 text-xs"
                value={template}
                onChange={(e) => handleTemplateChange(e.target.value)}
              >
                {TEMPLATES.map((t) => (
                  <option key={t} value={t}>{t === "None" ? "No template" : t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div />
          </div>

          {template !== "None" && Object.keys(templateVars).length > 0 && (
            <div className="space-y-2 p-3 rounded bg-white/[0.02] border border-white/[0.06]">
              <p className="text-[11px] font-medium text-[#8a8f98]">Template Variables</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(templateVars).map(([key]) => (
                  <div key={key}>
                    <label className="block text-[10px] text-[#62666d] mb-0.5">{key.replace(/_/g, " ")}</label>
                    <input
                      className="linear-input w-full px-3 py-1.5 text-xs"
                      placeholder={key}
                      value={templateVars[key]}
                      onChange={(e) => setTemplateVars({ ...templateVars, [key]: e.target.value })}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Related Entity Type (optional)</label>
              <select
                className="linear-input w-full px-3 py-1.5 text-xs"
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
              >
                <option value="">None</option>
                <option value="seeker">Seeker</option>
                <option value="contract">Contract</option>
                <option value="client">Client</option>
                <option value="match">Match</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Related Entity ID (optional)</label>
              <input
                type="number"
                className="linear-input w-full px-3 py-1.5 text-xs"
                placeholder="123"
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-white/[0.06]">
            <button
              onClick={handlePreview}
              disabled={previewLoading}
              className="text-[#8a8f98] hover:text-[#d0d6e0] text-xs font-medium px-4 py-1.5 rounded-md border border-white/10 transition disabled:opacity-50"
            >
              {previewLoading ? "Loading…" : "Preview"}
            </button>
            <button
              onClick={handleSend}
              disabled={sending}
              className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-4 py-1.5 rounded-md transition shadow disabled:opacity-50"
            >
              {sending ? "Sending…" : "Send Email"}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <label className="text-[11px] font-medium text-[#8a8f98]">Filter by status</label>
            <select
              className="linear-input px-3 py-1.5 text-xs"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
            >
              <option value="">All</option>
              <option value="queued">Queued</option>
              <option value="sent">Sent</option>
              <option value="delivered">Delivered</option>
              <option value="opened">Opened</option>
              <option value="bounced">Bounced</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {historyLoading && history.length === 0 ? (
            <Loading label="Loading history…" />
          ) : history.length === 0 ? (
            <EmptyState text="No emails sent yet." />
          ) : (
            <div className="linear-card overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/[0.06] text-[#8a8f98]">
                    <th className="text-left px-4 py-2.5 font-medium">To</th>
                    <th className="text-left px-4 py-2.5 font-medium">Subject</th>
                    <th className="text-left px-4 py-2.5 font-medium">Template</th>
                    <th className="text-left px-4 py-2.5 font-medium">Status</th>
                    <th className="text-left px-4 py-2.5 font-medium">Sent At</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((e) => (
                    <tr key={e.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition">
                      <td className="px-4 py-2.5 text-[#d0d6e0]">{e.to_email}</td>
                      <td className="px-4 py-2.5 text-[#f7f8f8]">{e.subject}</td>
                      <td className="px-4 py-2.5 text-[#8a8f98]">{e.template_name?.replace(/_/g, " ") ?? "—"}</td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${STATUS_COLORS[e.status] ?? "bg-white/10 text-[#8a8f98]"}`}>
                          {e.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-[#8a8f98]">{new Date(e.sent_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {hasMore && (
                <div className="p-3 border-t border-white/[0.06]">
                  <button
                    onClick={() => loadHistory(false)}
                    disabled={historyLoading}
                    className="text-[11px] text-[#5e6ad2] hover:text-[#7b82e8] transition"
                  >
                    {historyLoading ? "Loading…" : "Load more"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <Modal open={previewOpen} title="Email Preview" onClose={() => setPreviewOpen(false)} wide>
        <div className="space-y-3">
          <div className="text-[11px] text-[#8a8f98]">
            <span className="font-medium text-[#d0d6e0]">To:</span> {toEmail || "—"}
          </div>
          <div className="text-[11px] text-[#8a8f98]">
            <span className="font-medium text-[#d0d6e0]">Subject:</span> {subject || "—"}
          </div>
          <div className="border-t border-white/[0.06] pt-3">
            <div
              className="text-xs text-[#d0d6e0] leading-relaxed"
              dangerouslySetInnerHTML={{ __html: previewHtml || body }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
