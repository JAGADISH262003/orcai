"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api, ApiError, pollJob } from "@/lib/client";
import { useApp } from "@/components/AppShell";
import type { InboundMessage } from "@/lib/types";

const CHANNEL_TONE: Record<string, string> = {
  whatsapp: "emerald",
  telegram: "blue",
  indeed: "brand",
};

export default function InboundPage() {
  const { session } = useApp();
  const [messages, setMessages] = useState<InboundMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [simOpen, setSimOpen] = useState(false);
  const [body, setBody] = useState("");
  const [channel, setChannel] = useState("whatsapp");
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setMessages(await api.inbound());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load inbound feeds");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function simulate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const job = await api.ingestInbound({ agency_slug: session?.agency?.slug ?? "", channel, body });
      await pollJob(job.id);
      setBody("");
      setSimOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? (err.message as string) : "Simulation failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Loading inbound feeds…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">WhatsApp / Telegram Inbound</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Tier-1 free sourcing: incoming messages are classified into verified seekers automatically.
          </p>
        </div>
        <button
          onClick={() => setSimOpen(true)}
          className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
        >
          ⚡ Simulate inbound message
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 overflow-x-auto linear-card">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
                <th className="py-2.5 px-3">Channel</th>
                <th className="py-2.5 px-3">Sender</th>
                <th className="py-2.5 px-3">Message</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
              {messages.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-[#62666d]">
                    No inbound messages yet. Simulate one to see the pipeline.
                  </td>
                </tr>
              ) : (
                messages.map((m) => (
                  <tr key={m.id} className="hover:bg-white/[0.02] align-top">
                    <td className="py-3 px-3">
                      <Badge tone={CHANNEL_TONE[m.channel] ?? "slate"}>{m.channel}</Badge>
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-medium text-[#f7f8f8]">{m.sender_name ?? "—"}</div>
                      <div className="text-[10px] text-[#8a8f98] font-mono">{m.phone_number ?? ""}</div>
                    </td>
                    <td className="py-3 px-3 text-[#d0d6e0] max-w-md">
                      <span className="line-clamp-3">{m.body}</span>
                    </td>
                    <td className="py-3 px-3">
                      <Badge tone={m.status === "seeker_created" ? "emerald" : "amber"} mono>
                        {m.status}
                      </Badge>
                      {m.seeker_id ? (
                        <div className="text-[10px] text-brand-light mt-1">seeker id {m.seeker_id}</div>
                      ) : null}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="linear-card p-5 space-y-4 self-start">
          <h2 className="text-sm font-semibold">Webhook setup</h2>
          <p className="text-[11px] text-[#8a8f98] leading-relaxed">
            Point your WhatsApp Cloud API / Telegram bot at the backend:
          </p>
          <div className="space-y-2 font-mono text-[10px] text-[#d0d6e0]">
            <div className="p-2 rounded bg-white/[0.03] break-all">
              POST /api/v1/inbound/whatsapp/webhook
            </div>
            <div className="p-2 rounded bg-white/[0.03] break-all">
              POST /api/v1/inbound/telegram/webhook
            </div>
            <div className="p-2 rounded bg-white/[0.03] break-all">
              POST /api/v1/inbound/message (simulate)
            </div>
          </div>
          <p className="text-[10px] text-[#62666d]">
            Add WHATSAPP_VERIFY_TOKEN, WHATSAPP_PHONE_NUMBER_ID and TELEGRAM_BOT_TOKEN in your env
            to go live.
          </p>
        </div>
      </div>

      {simOpen ? (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="linear-card bg-[#0f1011] w-full max-w-xl p-6 space-y-4 border border-white/10 shadow-2xl">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-semibold">Simulate Inbound Message</h3>
              <button onClick={() => setSimOpen(false)} className="text-[#8a8f98]">✕</button>
            </div>
            <form onSubmit={simulate} className="space-y-4">
              <select value={channel} onChange={(e) => setChannel(e.target.value)} className="linear-input w-full px-3 py-2 text-xs">
                <option value="whatsapp">WhatsApp Cloud API</option>
                <option value="telegram">Telegram Bot</option>
                <option value="indeed">Indeed (free inbound)</option>
              </select>
              <textarea
                required
                rows={5}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="linear-input w-full p-3 text-xs"
                placeholder={"Hi, I am Rahul Verma, AWS DevOps Lead with 8 years of experience. Skills: AWS, Kubernetes, Terraform. H1B visa."}
              />
              <div className="flex justify-end space-x-2 pt-3 border-t border-white/[0.08]">
                <button type="button" onClick={() => setSimOpen(false)} className="px-4 py-1.5 rounded bg-white/[0.08] text-white text-xs">Cancel</button>
                <button disabled={busy} className="px-4 py-1.5 rounded bg-brand text-white text-xs disabled:opacity-50">
                  {busy ? "Processing…" : "Ingest message"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}