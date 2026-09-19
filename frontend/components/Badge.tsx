import React from "react";

const toneMap: Record<string, string> = {
  emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  red: "bg-red-500/10 text-red-400 border-red-500/20",
  purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  brand: "bg-brand/10 text-brand-light border-brand/20",
  slate: "bg-white/[0.06] text-[#8a8f98] border-white/10",
};

export function toneForStatus(status: string): string {
  switch (status) {
    case "active":
    case "approved":
    case "placed":
    case "confirmed":
      return "emerald";
    case "pending":
    case "pending_review":
      return "amber";
    case "submitted":
    case "trialing":
      return "blue";
    case "rejected":
    case "filled":
    case "closed":
    case "erased":
      return "red";
    case "A":
    default:
      return "brand";
  }
}

export function Badge({
  children,
  tone = "slate",
  mono = false,
}: {
  children: React.ReactNode;
  tone?: string;
  mono?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-medium ${toneMap[tone] ?? toneMap.slate} ${
        mono ? "font-mono" : ""
      }`}
    >
      {children}
    </span>
  );
}

export function TierBadge({ tier }: { tier: string }) {
  const tone = tier === "A" ? "emerald" : tier === "B" ? "amber" : "slate";
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
        toneMap[tone]
      }`}
    >
      Tier {tier}
    </span>
  );
}

export function MetricCard({
  label,
  value,
  hint,
  accent,
  sub,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  accent?: string;
  sub?: React.ReactNode;
}) {
  return (
    <div className="linear-card p-4">
      <div className="flex justify-between text-xs text-[#8a8f98] mb-2">
        <span>{label}</span>
        {hint}
      </div>
      <div className={`text-2xl font-semibold text-[#f7f8f8] ${accent ?? ""}`}>{value}</div>
      {sub ? (
        <div className="mt-2 text-[11px] text-[#62666d] flex justify-between">
          {sub}
        </div>
      ) : null}
    </div>
  );
}