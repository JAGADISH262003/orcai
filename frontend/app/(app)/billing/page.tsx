"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";
import type { Plan, Subscription } from "@/lib/types";
import { useApp } from "@/components/AppShell";

export default function BillingPage() {
  const { session, refresh } = useApp();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, s] = await Promise.all([api.plans(), api.subscription()]);
      setPlans(p);
      setSub(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load billing");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function select(slug: string) {
    setBusy(slug);
    try {
      const updated = await api.selectPlan(slug);
      setSub(updated);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan selection failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <Loading label="Loading pricing…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  const currentTier = sub?.tier ?? session?.agency.tier ?? "starter";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">SaaS Pricing & Subscription</h1>
        <p className="text-xs text-[#8a8f98] mt-1">
          {session?.agency.name} · current plan:{" "}
          <span className="text-brand-light font-mono">{currentTier}</span> ·{" "}
          {sub?.status ?? "trialing"}
        </p>
      </div>

      {sub ? (
        <div className="linear-card p-5 flex flex-wrap gap-6 text-xs">
          <div>
            <div className="text-[#8a8f98]">Plan</div>
            <div className="text-base font-semibold mt-1 capitalize">{sub.tier}</div>
          </div>
          <div>
            <div className="text-[#8a8f98]">Price</div>
            <div className="text-base font-semibold mt-1 font-mono">
              ₹{sub.price_per_month.toLocaleString("en-IN")}/mo
            </div>
          </div>
          <div>
            <div className="text-[#8a8f98]">Seats</div>
            <div className="text-base font-semibold mt-1">{sub.seats}</div>
          </div>
          <div>
            <div className="text-[#8a8f98]">Cycle</div>
            <div className="text-base font-semibold mt-1 font-mono">
              {sub.billing_cycle_start} → {sub.billing_cycle_end ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-[#8a8f98]">Status</div>
            <div className="mt-1">
              <Badge tone={sub.status === "active" ? "emerald" : "amber"}>{sub.status}</Badge>
            </div>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((p) => {
          const isCurrent = p.slug === currentTier;
          return (
            <div
              key={p.slug}
              className={`linear-card p-6 space-y-4 ${isCurrent ? "border-brand bg-gradient-to-b from-brand/10 to-transparent" : ""}`}
            >
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-[#f7f8f8]">{p.name}</h3>
                {isCurrent ? <Badge tone="brand">Current</Badge> : null}
              </div>
              <div className="text-2xl font-bold text-white">
                ₹{p.price_per_month.toLocaleString("en-IN")}{" "}
                <span className="text-xs text-[#8a8f98] font-normal">/ mo</span>
              </div>
              <p className="text-xs text-[#8a8f98]">{p.description}</p>
              <button
                disabled={isCurrent || busy !== null}
                onClick={() => select(p.slug)}
                className={`w-full py-2 text-xs font-medium rounded transition disabled:opacity-50 ${
                  isCurrent
                    ? "bg-white/[0.08] text-[#8a8f98] cursor-default"
                    : "bg-brand text-white shadow hover:bg-brand-hover"
                }`}
              >
                {busy === p.slug ? "Switching…" : isCurrent ? "Active plan" : "Switch to " + p.name}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}