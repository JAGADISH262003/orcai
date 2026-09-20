"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

import { CommandPalette } from "@/components/CommandPalette";
import { ToastProvider, useToast } from "@/components/Toast";
import { fetchMe, logout, api } from "@/lib/client";
import type { Session } from "@/lib/types";

interface AppContextValue {
  session: Session | null;
  refresh: () => Promise<void>;
}

const AppContext = createContext<AppContextValue>({ session: null, refresh: async () => {} });

export const useApp = () => useContext(AppContext);

const NAV: Array<{ href: string; label: string; icon: string; perm?: string }> = [
  { href: "/dashboard", label: "Command Center", icon: "◆" },
  { href: "/pipeline", label: "Matching & Submissions", icon: "◈", perm: "matches.read" },
  { href: "/contracts", label: "Employer Contracts", icon: "▣", perm: "contracts.read" },
  { href: "/seekers", label: "Talent Pool", icon: "◉", perm: "seekers.read" },
  { href: "/clients", label: "Clients", icon: "🏢", perm: "contracts.read" },
  { href: "/campaigns", label: "Campaigns", icon: "📢", perm: "seekers.read" },
  { href: "/interviews", label: "Interviews", icon: "📅", perm: "matches.read" },
  { href: "/offers", label: "Offer Management", icon: "📝", perm: "contracts.write" },
  { href: "/ai-screening", label: "AI Resume Screening", icon: "🤖", perm: "matches.write" },
  { href: "/scrapers", label: "Job & Candidate Scrapers", icon: "🔍", perm: "seekers.read" },
  { href: "/import", label: "Bulk Import", icon: "📥", perm: "seekers.write" },
  { href: "/hitl", label: "HITL Confidence Gate", icon: "⚠", perm: "hitl.read" },
  { href: "/inbound", label: "WhatsApp / Telegram Inbound", icon: "☏", perm: "seekers.read" },
  { href: "/tools", label: "Tools & Compliance", icon: "🛠", perm: "settings.write" },
  { href: "/audit", label: "Audit Log", icon: "📋", perm: "settings.write" },
  { href: "/dpdpa", label: "DPDPA Consent Ledger", icon: "⚖", perm: "settings.write" },
  { href: "/email", label: "Email", icon: "✉" },
  { href: "/activity", label: "Activity", icon: "📊" },
  { href: "/notifications", label: "Notifications", icon: "🔔" },
  { href: "/team", label: "Team", icon: "👥", perm: "teams.manage" },
  { href: "/settings", label: "Settings", icon: "⚙", perm: "settings.write" },
  { href: "/billing", label: "Pricing & ROI", icon: "₹", perm: "billing.read" },
];

const MOBILE_BOTTOM_NAV = [
  { href: "/dashboard", label: "Home", icon: "◆" },
  { href: "/pipeline", label: "Pipeline", icon: "◈" },
  { href: "/contracts", label: "Contracts", icon: "▣" },
  { href: "/seekers", label: "Talent", icon: "◉" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const stored = localStorage.getItem("orcai-theme") as "dark" | "light" | null;
    const initial = stored ?? "dark";
    setTheme(initial);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(initial);
  }, []);

  const toggle = useCallback(() => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("orcai-theme", next);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(next);
  }, [theme]);

  return (
    <button
      onClick={toggle}
      className="w-8 h-8 rounded-md flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/[0.06] transition"
      aria-label="Toggle theme"
    >
      {theme === "dark" ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}

function HamburgerButton({ onClick, open }: { onClick: () => void; open: boolean }) {
  return (
    <button
      onClick={onClick}
      className="lg:hidden w-8 h-8 rounded-md flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/[0.06] transition"
      aria-label="Toggle menu"
    >
      {open ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      )}
    </button>
  );
}

function CmdKHint({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="hidden md:flex items-center gap-2 text-[11px] text-[var(--text-dim)] bg-[var(--bg-card)] border border-[var(--border-default)] rounded-md px-2.5 py-1.5 hover:border-[var(--border-hover)] transition"
    >
      <span>⌘K</span>
      <span>Search</span>
    </button>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <AppShellInner>{children}</AppShellInner>
    </ToastProvider>
  );
}

function AppShellInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);

  useEffect(() => {
    fetchMe()
      .then((s) => {
        if (!s) {
          router.replace("/login");
          return;
        }
        setSession(s);
        api.unreadCount().then((r) => setUnreadCount(r.count)).catch(() => {});
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  async function refresh() {
    const s = await fetchMe();
    if (s) setSession(s);
  }

  async function doLogout() {
    await logout();
    router.replace("/login");
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-xs text-[var(--text-muted)]">
        Verifying session…
      </div>
    );
  }
  if (!session) return null;

  const perms = session.user.permissions ?? [];
  const canWriteContracts = perms.includes("contracts.write");
  const visibleNav = NAV.filter((item) => !item.perm || perms.includes(item.perm));
  const initial = (session.user.name || "U").slice(0, 2).toUpperCase();

  return (
    <AppContext.Provider value={{ session, refresh }}>
      <div className="min-h-screen flex flex-col">
        <header className="h-14 border-b border-[var(--border-default)] bg-[var(--header-bg)] backdrop-blur sticky top-0 z-40 flex items-center justify-between px-4 md:px-6">
          <div className="flex items-center space-x-3">
            <HamburgerButton onClick={() => setSidebarOpen(!sidebarOpen)} open={sidebarOpen} />
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded bg-gradient-to-br from-[var(--accent)] to-indigo-600 flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-[var(--accent)]/20">
                O
              </div>
              <span className="font-semibold tracking-tight text-[var(--text-primary)] text-base">
                ORCAI{" "}
                <span className="text-xs px-2 py-0.5 rounded bg-[var(--accent-bg)] text-[var(--accent-light)] font-mono font-medium ml-1">
                  {session.agency.name}
                </span>
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-2 md:space-x-3">
            <CmdKHint onClick={() => setCmdOpen(true)} />
            {canWriteContracts ? (
              <Link
                href="/contracts"
                className="hidden sm:inline-flex bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
              >
                + Post Requisition
              </Link>
            ) : null}
            <ThemeToggle />
            <Link href="/notifications" className="relative text-[var(--text-muted)] hover:text-[var(--text-primary)] transition p-1.5">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Link>
            <div className="flex items-center space-x-2">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-medium text-[var(--text-primary)]">{session.user.name}</div>
                <div className="text-[10px] text-[var(--text-muted)]">{session.user.role}</div>
              </div>
              <div className="w-8 h-8 rounded-full bg-[var(--bg-card)] border border-[var(--border-default)] flex items-center justify-center text-xs font-semibold text-[var(--text-primary)]">
                {initial}
              </div>
            </div>
            <button
              onClick={doLogout}
              className="text-[10px] text-[var(--text-muted)] hover:text-[var(--text-primary)] px-2 py-1 rounded border border-[var(--border-default)]"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          {/* Desktop sidebar */}
          <aside className="w-60 border-r border-[var(--border-default)] bg-[var(--sidebar-bg)] hidden lg:flex flex-col justify-between p-4">
            <div>
              <p className="text-[11px] font-mono text-[var(--text-dim)] uppercase tracking-wider px-3 mb-2">
                Workspace
              </p>
              <nav className="space-y-0.5">
                {visibleNav.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(item.href + "/");
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center space-x-3 px-3 py-2 rounded-md text-xs font-medium transition ${
                        active
                          ? "text-[var(--text-primary)] bg-[var(--bg-card)]"
                          : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]"
                      }`}
                    >
                      <span className="w-4 text-center text-[var(--accent-light)]">{item.icon}</span>
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
            <div className="pt-4 border-t border-[var(--border-default)]">
              <div className="linear-card p-3 bg-gradient-to-br from-[var(--accent)]/10 to-transparent">
                <p className="text-[11px] font-semibold text-[var(--text-primary)] mb-1">
                  Dual Marketplace Model
                </p>
                <p className="text-[10px] text-[var(--text-muted)] mb-2">
                  Employer contracts matched with verified employment seekers.
                </p>
              </div>
            </div>
          </aside>

          {/* Mobile sidebar overlay */}
          {sidebarOpen && (
            <div className="fixed inset-0 z-50 lg:hidden" onClick={() => setSidebarOpen(false)}>
              <div className="absolute inset-0 bg-[var(--overlay-bg)]" />
              <aside
                className="absolute left-0 top-0 bottom-0 w-64 bg-[var(--sidebar-bg)] border-r border-[var(--border-default)] flex flex-col justify-between p-4 sidebar-enter overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-semibold text-[var(--text-primary)]">Menu</span>
                    <button
                      onClick={() => setSidebarOpen(false)}
                      className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <nav className="space-y-0.5">
                    {visibleNav.map((item) => {
                      const active = pathname === item.href || pathname.startsWith(item.href + "/");
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={`flex items-center space-x-3 px-3 py-2.5 rounded-md text-xs font-medium transition ${
                            active
                              ? "text-[var(--text-primary)] bg-[var(--bg-card)]"
                              : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]"
                          }`}
                        >
                          <span className="w-4 text-center text-[var(--accent-light)]">{item.icon}</span>
                          <span>{item.label}</span>
                        </Link>
                      );
                    })}
                  </nav>
                </div>
              </aside>
            </div>
          )}

          <main className="flex-1 overflow-y-auto bg-[var(--bg-page)] p-6 lg:p-8 pb-20 lg:pb-8">{children}</main>
        </div>

        {/* Mobile bottom nav */}
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-[var(--bg-surface)] border-t border-[var(--border-default)] flex items-center justify-around px-2 py-1 safe-area-inset-bottom">
          {MOBILE_BOTTOM_NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-md text-[10px] font-medium transition min-w-[56px] ${
                  active
                    ? "text-[var(--accent-light)]"
                    : "text-[var(--text-muted)]"
                }`}
              >
                <span className="text-base">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
      </div>
    </AppContext.Provider>
  );
}
