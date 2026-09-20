"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";

import { Badge, TierBadge, toneForStatus } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api, ApiError } from "@/lib/client";
import type { Match } from "@/lib/types";

export default function MatchDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [match, setMatch] = useState<Match | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [reviewText, setReviewText] = useState("");
  const [reviewing, setReviewing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const m = await api.match(id);
      setMatch(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load match");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) load();
  }, [id, load]);

  async function handleReview(decision: "approve" | "reject") {
    setReviewing(true);
    try {
      const updated = await api.reviewHitl(id, decision, reviewText || undefined);
      setMatch(updated);
      setReviewText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setReviewing(false);
    }
  }

  if (loading) return <Loading label="Loading match…" />;
  if (error && !match) return <ErrorBanner message={error} onRetry={load} />;
  if (!match) return <EmptyState text="Match not found" />;

  const scoreColor =
    match.score >= 80 ? "text-emerald-400" :
    match.score >= 60 ? "text-amber-400" :
    "text-red-400";

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} />}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="text-[#8a8f98] hover:text-white text-xs">
            ← Back
          </button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Match #{match.id}</h1>
            <p className="text-xs text-[#8a8f98] mt-1">
              {match.seeker_name ?? `Seeker #${match.seeker_id}`} → {match.contract_title ?? `Contract #${match.contract_id}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <TierBadge tier={match.tier} />
          <Badge tone={toneForStatus(match.status)}>{match.status}</Badge>
          {match.hitl_required && (
            <Badge tone="amber">HITL Required</Badge>
          )}
        </div>
      </div>

      {/* Score Gauge + Info Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Score Gauge */}
        <div className="linear-card p-6 flex flex-col items-center justify-center space-y-2">
          <p className="text-[11px] text-[#8a8f98] font-medium uppercase tracking-wider">Match Score</p>
          <div className={`text-5xl font-bold font-mono ${scoreColor}`}>
            {match.score}%
          </div>
          <TierBadge tier={match.tier} />
          <p className="text-[10px] text-[#62666d]">
            Created {new Date(match.created_at).toLocaleString()}
          </p>
        </div>

        {/* Seeker Card */}
        <div className="linear-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Seeker</h2>
          <div
            className="cursor-pointer hover:bg-white/[0.02] rounded p-2 -m-2 transition"
            onClick={() => router.push(`/seekers/${match.seeker_id}`)}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-brand/15 flex items-center justify-center font-bold text-brand-light text-xs">
                {(match.seeker_name ?? "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium text-[#f7f8f8]">{match.seeker_name ?? `Seeker #${match.seeker_id}`}</p>
                <p className="text-[10px] text-[#8a8f98]">{match.seeker_headline ?? "—"}</p>
              </div>
            </div>
          </div>
          {match.seeker_skills.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {match.seeker_skills.slice(0, 8).map((s) => (
                <span key={s} className="px-1.5 py-0.5 rounded bg-brand/10 text-brand-light text-[10px]">{s}</span>
              ))}
              {match.seeker_skills.length > 8 && (
                <span className="text-[10px] text-[#62666d]">+{match.seeker_skills.length - 8}</span>
              )}
            </div>
          )}
        </div>

        {/* Contract Card */}
        <div className="linear-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Contract</h2>
          <div
            className="cursor-pointer hover:bg-white/[0.02] rounded p-2 -m-2 transition"
            onClick={() => router.push(`/contracts/${match.contract_id}`)}
          >
            <p className="text-sm font-medium text-[#f7f8f8]">{match.contract_title ?? `Contract #${match.contract_id}`}</p>
          </div>
        </div>
      </div>

      {/* AI Rationale */}
      {match.rationale && (
        <div className="linear-card p-5 space-y-2">
          <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">AI Rationale</h2>
          <div className="p-3 rounded bg-black/40 border border-white/[0.06] text-xs">
            <p className="text-[#d0d6e0] leading-relaxed whitespace-pre-wrap">{match.rationale}</p>
          </div>
        </div>
      )}

      {/* HITL Section */}
      {match.hitl_required && (
        <div className="linear-card p-5 space-y-3 border-l-4 border-amber-500">
          <h2 className="text-sm font-semibold text-amber-400 border-b border-white/[0.06] pb-2">
            Human-in-the-Loop Review
          </h2>
          {match.hitl_status === "approved" || match.hitl_status === "rejected" ? (
            <div className="p-3 rounded bg-black/40 border border-white/[0.06] text-xs space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[#8a8f98]">Decision:</span>
                <Badge tone={match.hitl_status === "approved" ? "emerald" : "red"}>{match.hitl_status}</Badge>
              </div>
              {match.human_review && (
                <p className="text-[#d0d6e0] mt-2">{match.human_review}</p>
              )}
              {match.reviewed_at && (
                <p className="text-[10px] text-[#62666d] mt-1">Reviewed {new Date(match.reviewed_at).toLocaleString()}</p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                className="linear-input w-full px-3 py-2 text-xs"
                rows={3}
                placeholder="Add review rationale (optional)…"
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleReview("reject")}
                  disabled={reviewing}
                  className="px-4 py-1.5 rounded bg-red-500/10 text-red-400 text-xs font-medium transition hover:bg-red-500/20 disabled:opacity-50"
                >
                  {reviewing ? "Processing…" : "Reject"}
                </button>
                <button
                  onClick={() => handleReview("approve")}
                  disabled={reviewing}
                  className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition disabled:opacity-50"
                >
                  {reviewing ? "Processing…" : "Approve"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Timeline */}
      <div className="linear-card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-[#f7f8f8] border-b border-white/[0.06] pb-2">Timeline</h2>
        <div className="space-y-3 text-xs">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-brand shrink-0" />
            <div>
              <p className="text-[#d0d6e0]">Match created</p>
              <p className="text-[10px] text-[#62666d]">{new Date(match.created_at).toLocaleString()}</p>
            </div>
          </div>
          {match.reviewed_at && (
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full shrink-0 ${match.hitl_status === "approved" ? "bg-emerald-400" : "bg-red-400"}`} />
              <div>
                <p className="text-[#d0d6e0]">
                  Reviewed — <Badge tone={match.hitl_status === "approved" ? "emerald" : "red"}>{match.hitl_status}</Badge>
                </p>
                <p className="text-[10px] text-[#62666d]">{new Date(match.reviewed_at).toLocaleString()}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
