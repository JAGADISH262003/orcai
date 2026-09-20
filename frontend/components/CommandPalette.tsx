"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

interface CommandItem {
  id: string;
  label: string;
  icon: string;
  href?: string;
  action?: () => void;
  category: string;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

const STATIC_COMMANDS: Omit<CommandItem, "id">[] = [
  { label: "Dashboard", icon: "◆", href: "/dashboard", category: "Navigation" },
  { label: "Matching & Submissions", icon: "◈", href: "/pipeline", category: "Navigation" },
  { label: "Employer Contracts", icon: "▣", href: "/contracts", category: "Navigation" },
  { label: "Talent Pool", icon: "◉", href: "/seekers", category: "Navigation" },
  { label: "Clients", icon: "🏢", href: "/clients", category: "Navigation" },
  { label: "Interviews", icon: "📅", href: "/interviews", category: "Navigation" },
  { label: "Settings", icon: "⚙", href: "/settings", category: "Navigation" },
  { label: "New Contract", icon: "＋", href: "/contracts", category: "Actions" },
  { label: "New Seeker", icon: "＋", href: "/seekers", category: "Actions" },
  { label: "Run Matching", icon: "⚡", href: "/pipeline", category: "Actions" },
  { label: "Bulk Import", icon: "📥", href: "/import", category: "Actions" },
  { label: "Audit Log", icon: "📋", href: "/audit", category: "Navigation" },
  { label: "Notifications", icon: "🔔", href: "/notifications", category: "Navigation" },
  { label: "Team Management", icon: "👥", href: "/team", category: "Navigation" },
  { label: "Pricing & ROI", icon: "₹", href: "/billing", category: "Navigation" },
  { label: "Job Scrapers", icon: "🔍", href: "/scrapers", category: "Navigation" },
  { label: "DPDPA Consent", icon: "⚖", href: "/dpdpa", category: "Navigation" },
  { label: "Tools & Compliance", icon: "🛠", href: "/tools", category: "Navigation" },
  { label: "Email", icon: "✉", href: "/email", category: "Navigation" },
  { label: "Activity", icon: "📊", href: "/activity", category: "Navigation" },
];

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const commands: CommandItem[] = useMemo(
    () => STATIC_COMMANDS.map((c, i) => ({ ...c, id: `cmd-${i}` })),
    [],
  );

  const filtered = useMemo(() => {
    if (!query) return commands;
    const q = query.toLowerCase();
    return commands.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q),
    );
  }, [query, commands]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const execute = useCallback(
    (item: CommandItem) => {
      onClose();
      if (item.href) {
        router.push(item.href);
      } else if (item.action) {
        item.action();
      }
    },
    [onClose, router],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filtered[selectedIndex]) execute(filtered[selectedIndex]);
      } else if (e.key === "Escape") {
        onClose();
      }
    },
    [filtered, selectedIndex, execute, onClose],
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (open) {
          onClose();
        } else {
          // Parent should toggle open
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (listRef.current) {
      const el = listRef.current.children[selectedIndex] as HTMLElement;
      el?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[90] cmd-overlay" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="relative max-w-lg mx-auto mt-[15vh] px-4">
        <div
          className="cmd-panel bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl shadow-2xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center px-4 border-b border-[var(--border-default)]">
            <span className="text-[var(--text-muted)] text-sm mr-3">⌘</span>
            <input
              ref={inputRef}
              type="text"
              placeholder="Type a command or search…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-dim)] outline-none"
            />
            <kbd className="text-[10px] text-[var(--text-dim)] bg-[var(--bg-card)] border border-[var(--border-default)] rounded px-1.5 py-0.5 ml-2">
              esc
            </kbd>
          </div>

          <div ref={listRef} className="max-h-80 overflow-y-auto py-2">
            {filtered.length === 0 && (
              <div className="px-4 py-6 text-center text-xs text-[var(--text-muted)]">
                No results found
              </div>
            )}
            {filtered.map((item, i) => (
              <button
                key={item.id}
                onClick={() => execute(item)}
                onMouseEnter={() => setSelectedIndex(i)}
                className={`w-full flex items-center gap-3 px-4 py-2 text-left text-sm transition ${
                  i === selectedIndex
                    ? "bg-[var(--accent-bg)] text-[var(--text-primary)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-card)]"
                }`}
              >
                <span className="w-5 text-center text-xs">{item.icon}</span>
                <span className="flex-1">{item.label}</span>
                <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">
                  {item.category}
                </span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4 px-4 py-2 border-t border-[var(--border-default)] text-[10px] text-[var(--text-dim)]">
            <span>↑↓ navigate</span>
            <span>↵ select</span>
            <span>esc close</span>
          </div>
        </div>
      </div>
    </div>
  );
}
