"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import React, { createContext, useContext, useEffect, useState } from "react";

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
  { href: "/interviews", label: "Interviews", icon: "📅", perm: "matches.read" },
  { href: "/scrapers", label: "Job & Candidate Scrapers", icon: "🔍", perm: "seekers.read" },
  { href: "/import", label: "Bulk Import", icon: "📥", perm: "seekers.write" },
  { href: "/hitl", label: "HITL Confidence Gate", icon: "⚠", perm: "hitl.read" },
  { href: "/inbound", label: "WhatsApp / Telegram Inbound", icon: "☏", perm: "seekers.read" },
  { href: "/tools", label: "Tools & Compliance", icon: "🛠", perm: "settings.write" },
  { href: "/audit", label: "Audit Log", icon: "📋", perm: "settings.write" },
  { href: "/dpdpa", label: "DPDPA Consent Ledger", icon: "⚖", perm: "settings.write" },
  { href: "/notifications", label: "Notifications", icon: "🔔" },
  { href: "/team", label: "Team", icon: "👥", perm: "teams.manage" },
  { href: "/settings", label: "Settings", icon: "⚙", perm: "settings.write" },
  { href: "/billing", label: "Pricing & ROI", icon: "₹", perm: "billing.read" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

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
      <div className="min-h-screen flex items-center justify-center text-xs text-[#8a8f98]">
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
        <header className="h-14 border-b border-white/[0.08] bg-[#0f1011]/90 backdrop-blur sticky top-0 z-40 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded bg-gradient-to-br from-brand to-indigo-600 flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-brand/20">
                O
              </div>
              <span className="font-semibold tracking-tight text-[#f7f8f8] text-base">
                ORCAI{" "}
                <span className="text-xs px-2 py-0.5 rounded bg-brand/20 text-brand-light font-mono font-medium ml-1">
                  {session.agency.name}
                </span>
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {canWriteContracts ? (
              <Link
                href="/contracts"
                className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
              >
                + Post Requisition
              </Link>
            ) : null}
            <Link href="/notifications" className="relative text-[#8a8f98] hover:text-white transition p-1.5">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Link>
            <div className="flex items-center space-x-2">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-medium text-[#f7f8f8]">{session.user.name}</div>
                <div className="text-[10px] text-[#8a8f98]">{session.user.role}</div>
              </div>
              <div className="w-8 h-8 rounded-full bg-[#28282c] border border-white/10 flex items-center justify-center text-xs font-semibold text-[#f7f8f8]">
                {initial}
              </div>
            </div>
            <button
              onClick={doLogout}
              className="text-[10px] text-[#8a8f98] hover:text-white px-2 py-1 rounded border border-white/10"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          <aside className="w-60 border-r border-white/[0.08] bg-[#0f1011] hidden lg:flex flex-col justify-between p-4">
            <div>
              <p className="text-[11px] font-mono text-[#62666d] uppercase tracking-wider px-3 mb-2">
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
                          ? "text-[#f7f8f8] bg-white/[0.04]"
                          : "text-[#8a8f98] hover:text-[#f7f8f8] hover:bg-white/[0.02]"
                      }`}
                    >
                      <span className="w-4 text-center text-brand-light">{item.icon}</span>
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
            <div className="pt-4 border-t border-white/[0.08]">
              <div className="linear-card p-3 bg-gradient-to-br from-brand/10 to-transparent">
                <p className="text-[11px] font-semibold text-[#f7f8f8] mb-1">
                  Dual Marketplace Model
                </p>
                <p className="text-[10px] text-[#8a8f98] mb-2">
                  Employer contracts matched with verified employment seekers.
                </p>
              </div>
            </div>
          </aside>
          <main className="flex-1 overflow-y-auto bg-[#08090a] p-6 lg:p-8">{children}</main>
        </div>
      </div>
    </AppContext.Provider>
  );
}