"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, Loading, EmptyState } from "@/components/UI";
import { api } from "@/lib/client";
import type { ActivityEntry } from "@/lib/types";

const ENTITY_TYPES = ["all", "seeker", "contract", "match", "client", "interview"];

const ACTION_STYLES: Record<string, { icon: string; color: string }> = {
  created: { icon: "+", color: "bg-emerald-500/20 text-emerald-300" },
  updated: { icon: "✎", color: "bg-blue-500/20 text-blue-300" },
  status_changed: { icon: "◆", color: "bg-amber-500/20 text-amber-300" },
  note_added: { icon: "📝", color: "bg-purple-500/20 text-purple-300" },
  tag_attached: { icon: "🏷", color: "bg-indigo-500/20 text-indigo-300" },
  deleted: { icon: "✕", color: "bg-red-500/20 text-red-300" },
};

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function ActivityPage() {
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entityFilter, setEntityFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const LIMIT = 30;

  useEffect(() => {
    loadActivities(true);
  }, [entityFilter, actionFilter]);

  async function loadActivities(reset = false) {
    if (reset) setLoading(true);
    else setLoadingMore(true);
    setError(null);
    try {
      const params: Record<string, unknown> = { limit: LIMIT, offset: reset ? 0 : offset };
      if (entityFilter !== "all") params.entity_type = entityFilter;
      if (actionFilter) params.action = actionFilter;
      const data = await api.activityLog(params);
      if (reset) {
        setActivities(data);
        setOffset(data.length);
      } else {
        setActivities((prev) => [...prev, ...data]);
        setOffset((prev) => prev + data.length);
      }
      setHasMore(data.length === LIMIT);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load activities");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Activity Timeline</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Track all changes across your workspace.</p>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-[11px] font-medium text-[#8a8f98]">Entity</label>
          <select
            className="linear-input px-3 py-1.5 text-xs"
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
          >
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>{t === "all" ? "All" : t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[11px] font-medium text-[#8a8f98]">Action</label>
          <select
            className="linear-input px-3 py-1.5 text-xs"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="created">Created</option>
            <option value="updated">Updated</option>
            <option value="status_changed">Status Changed</option>
            <option value="note_added">Note Added</option>
            <option value="tag_attached">Tag Attached</option>
          </select>
        </div>
      </div>

      {loading ? (
        <Loading label="Loading activities…" />
      ) : activities.length === 0 ? (
        <EmptyState text="No activities found. Changes across your workspace will appear here." />
      ) : (
        <div className="linear-card divide-y divide-white/[0.04]">
          {activities.map((act) => {
            const style = ACTION_STYLES[act.action] ?? { icon: "•", color: "bg-white/10 text-[#8a8f98]" };
            return (
              <div key={act.id} className="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.02] transition">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] shrink-0 ${style.color}`}>
                  {style.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-[#d0d6e0]">
                    <span className="font-medium text-[#f7f8f8]">{act.user_name}</span>{" "}
                    {act.description}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-[#62666d]">{timeAgo(act.created_at)}</span>
                    {act.entity_type && act.entity_id && (
                      <a
                        href={`/${act.entity_type === "match" ? "pipeline" : act.entity_type + "s"}/${act.entity_id}`}
                        className="text-[10px] text-[#5e6ad2] hover:text-[#7b82e8] transition"
                      >
                        {act.entity_type} #{act.entity_id}
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {hasMore && activities.length > 0 && (
        <div className="flex justify-center">
          <button
            onClick={() => loadActivities(false)}
            disabled={loadingMore}
            className="text-[11px] text-[#5e6ad2] hover:text-[#7b82e8] transition px-4 py-1.5 rounded border border-white/[0.06]"
          >
            {loadingMore ? "Loading…" : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
}
