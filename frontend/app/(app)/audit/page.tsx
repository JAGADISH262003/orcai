"use client";

import { useEffect, useState } from "react";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";

interface AuditEntry {
  id: number;
  action: string;
  user_id: number;
  entity_type: string;
  entity_id: number;
  meta: unknown;
  ip: string;
  created_at: string;
}

interface AuditStats {
  total_events: number;
  events_this_week: number;
  by_action: Record<string, number>;
}

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
      <h1 className="text-xl font-bold">Audit Log</h1>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border rounded p-3 text-center">
            <p className="text-2xl font-bold text-blue-600">{stats.total_events}</p>
            <p className="text-xs text-gray-500">Total Events</p>
          </div>
          <div className="bg-white border rounded p-3 text-center">
            <p className="text-2xl font-bold text-green-600">{stats.events_this_week}</p>
            <p className="text-xs text-gray-500">This Week</p>
          </div>
          <div className="bg-white border rounded p-3 text-center">
            <p className="text-2xl font-bold text-purple-600">{Object.keys(stats.by_action).length}</p>
            <p className="text-xs text-gray-500">Unique Actions</p>
          </div>
        </div>
      )}

      <div className="flex gap-4 items-center">
        <label className="text-xs font-medium text-gray-500">Filter by action:</label>
        <input
          className="border rounded px-2 py-1 text-sm"
          placeholder="e.g. seeker.create"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        />
        {stats && (
          <div className="flex gap-2 flex-wrap text-xs">
            {Object.entries(stats.by_action).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([action, count]) => (
              <button
                key={action}
                className={`px-2 py-0.5 rounded border text-xs ${actionFilter === action ? "bg-blue-100 border-blue-300" : "hover:bg-gray-50"}`}
                onClick={() => setActionFilter(actionFilter === action ? "" : action)}
              >
                {action} ({count})
              </button>
            ))}
          </div>
        )}
      </div>

      {logs.length > 0 ? (
        <div className="overflow-x-auto border rounded">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="px-3 py-2 font-medium">Time</th>
                <th className="px-3 py-2 font-medium">Action</th>
                <th className="px-3 py-2 font-medium">Entity</th>
                <th className="px-3 py-2 font-medium">User ID</th>
                <th className="px-3 py-2 font-medium">IP</th>
                <th className="px-3 py-2 font-medium">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{log.action}</td>
                  <td className="px-3 py-2 text-xs">{log.entity_type}#{log.entity_id ?? "—"}</td>
                  <td className="px-3 py-2 text-xs">{log.user_id ?? "—"}</td>
                  <td className="px-3 py-2 text-xs text-gray-400">{log.ip ?? "—"}</td>
                  <td className="px-3 py-2 text-xs text-gray-400 max-w-xs truncate">
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
