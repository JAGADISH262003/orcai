"use client";

import { useEffect, useState } from "react";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type { AuditEntry, AuditStats } from "@/lib/types";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [actionFilter, setActionFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = actionFilter ? `?action=${encodeURIComponent(actionFilter)}` : "";
      const [l, s] = await Promise.all([api.auditLogs(params), api.auditStats()]);
      setLogs(l);
      setStats(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [actionFilter]);

  if (loading) return <Loading label="Loading audit logs..." />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Audit Log</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Track all user actions and system events across the platform.</p>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="linear-card p-4 text-center">
            <p className="text-2xl font-bold text-[#5e6ad2]">{stats.total_events}</p>
            <p className="text-[11px] text-[#8a8f98]">Total Events</p>
          </div>
          <div className="linear-card p-4 text-center">
            <p className="text-2xl font-bold text-green-400">{stats.events_this_week}</p>
            <p className="text-[11px] text-[#8a8f98]">This Week</p>
          </div>
          <div className="linear-card p-4 text-center">
            <p className="text-2xl font-bold text-purple-400">{Object.keys(stats.by_action).length}</p>
            <p className="text-[11px] text-[#8a8f98]">Unique Actions</p>
          </div>
        </div>
      )}

      <div className="flex gap-4 items-center flex-wrap">
        <label className="text-[11px] font-medium text-[#8a8f98]">Filter by action:</label>
        <input className="linear-input px-3 py-1.5 text-xs" placeholder="e.g. seeker.create" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} />
        {stats && (
          <div className="flex gap-2 flex-wrap">
            {Object.entries(stats.by_action).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([action, count]) => (
              <button key={action}
                className={`px-2 py-0.5 rounded text-[10px] transition ${actionFilter === action ? "bg-[#5e6ad2]/20 text-[#5e6ad2] border border-[#5e6ad2]/30" : "text-[#8a8f98] hover:text-[#d0d6e0] bg-white/[0.04]"}`}
                onClick={() => setActionFilter(actionFilter === action ? "" : action)}>
                {action} ({count})
              </button>
            ))}
          </div>
        )}
      </div>

      {logs.length > 0 ? (
        <div className="linear-card overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="text-left text-[10px] text-[#8a8f98] border-b border-white/[0.06]">
              <tr>
                <th className="px-3 py-2 font-medium">Time</th>
                <th className="px-3 py-2 font-medium">Action</th>
                <th className="px-3 py-2 font-medium">Entity</th>
                <th className="px-3 py-2 font-medium">User ID</th>
                <th className="px-3 py-2 font-medium">IP</th>
                <th className="px-3 py-2 font-medium">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-white/[0.02]">
                  <td className="px-3 py-2 text-[10px] text-[#8a8f98] whitespace-nowrap">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-[#d0d6e0]">{log.action}</td>
                  <td className="px-3 py-2 text-[#d0d6e0]">{log.entity_type}#{log.entity_id ?? "—"}</td>
                  <td className="px-3 py-2 text-[#d0d6e0]">{log.user_id ?? "—"}</td>
                  <td className="px-3 py-2 text-[#8a8f98]">{log.ip ?? "—"}</td>
                  <td className="px-3 py-2 text-[#8a8f98] max-w-xs truncate">
                    {log.meta ? JSON.stringify(log.meta) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState text={actionFilter ? "No events match this filter" : "No audit events yet"} />
      )}
    </div>
  );
}
