"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";

import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type { AppNotification } from "@/lib/types";

const TYPE_STYLES: Record<string, { icon: string; color: string; bg: string }> = {
  info: { icon: "ℹ", color: "text-blue-400", bg: "bg-blue-500/10" },
  success: { icon: "✓", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  warning: { icon: "⚠", color: "text-amber-400", bg: "bg-amber-500/10" },
  error: { icon: "✕", color: "text-red-400", bg: "bg-red-500/10" },
};

function getDateGroup(dateStr: string): "today" | "yesterday" | "earlier" {
  const d = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d >= today) return "today";
  if (d >= yesterday) return "yesterday";
  return "earlier";
}

export default function NotificationsPage() {
  const router = useRouter();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.notifications(filter === "unread");
      setNotifications(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function markRead(id: number) {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to mark as read");
    }
  }

  async function markAllRead() {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to mark all as read");
    }
  }

  function handleClick(n: AppNotification) {
    if (!n.is_read) markRead(n.id);
    if (n.action_url) router.push(n.action_url);
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const grouped: { label: string; key: string; items: AppNotification[] }[] = [];
  const groups: Record<string, AppNotification[]> = {};
  for (const n of notifications) {
    if (!n.created_at) continue;
    const g = getDateGroup(n.created_at);
    if (!groups[g]) groups[g] = [];
    groups[g].push(n);
  }
  if (groups.today) grouped.push({ label: "Today", key: "today", items: groups.today });
  if (groups.yesterday) grouped.push({ label: "Yesterday", key: "yesterday", items: groups.yesterday });
  if (groups.earlier) grouped.push({ label: "Earlier", key: "earlier", items: groups.earlier });

  if (loading) return <Loading label="Loading notifications…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Notifications</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Stay updated on matches, reviews, and system activity.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition"
            >
              Mark all as read ({unreadCount})
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 border-b border-white/[0.06] pb-2">
        {(["all", "unread"] as const).map((f) => (
          <button
            key={f}
            className={`px-3 py-1 text-xs font-medium rounded transition ${
              filter === f
                ? "bg-[#5e6ad2] text-white"
                : "text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-white/[0.04]"
            }`}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : "Unread"}
            {f === "unread" && unreadCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 text-[10px] font-mono">
                {unreadCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Notification List */}
      {notifications.length === 0 ? (
        <EmptyState text={filter === "unread" ? "All caught up — no unread notifications" : "No notifications yet"} />
      ) : (
        <div className="space-y-4">
          {grouped.map((group) => (
            <div key={group.key}>
              <p className="text-[11px] text-[#8a8f98] font-medium mb-2 px-1">{group.label}</p>
              <div className="space-y-1">
                {group.items.map((n) => {
                  const style = TYPE_STYLES[n.notification_type] ?? TYPE_STYLES.info;
                  return (
                    <div
                      key={n.id}
                      onClick={() => handleClick(n)}
                      className={`flex items-start gap-3 p-3 rounded border transition cursor-pointer ${
                        n.is_read
                          ? "bg-transparent border-white/[0.04] hover:bg-white/[0.02]"
                          : "bg-white/[0.03] border-white/[0.08] hover:bg-white/[0.05]"
                      }`}
                    >
                      <div className={`w-7 h-7 rounded-full ${style.bg} flex items-center justify-center shrink-0`}>
                        <span className={`text-xs ${style.color}`}>{style.icon}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className={`text-xs font-medium ${n.is_read ? "text-[#d0d6e0]" : "text-[#f7f8f8]"}`}>
                            {n.title}
                          </p>
                          {!n.is_read && <div className="w-1.5 h-1.5 rounded-full bg-brand shrink-0" />}
                        </div>
                        <p className="text-[11px] text-[#8a8f98] mt-0.5 line-clamp-2">{n.message}</p>
                        <p className="text-[10px] text-[#62666d] mt-1">{n.created_at ? new Date(n.created_at).toLocaleString() : ""}</p>
                      </div>
                      {n.action_url && (
                        <span className="text-[10px] text-brand-light shrink-0 mt-1">View →</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
