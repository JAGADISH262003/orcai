"use client";

import { useEffect, useState } from "react";

import { Badge, toneForStatus } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading, Modal } from "@/components/UI";
import { api, apiFetch, ApiError, pollJob } from "@/lib/client";
import type { Contract, Offer, Seeker } from "@/lib/types";

const COLUMNS = [
  { status: "draft", label: "Draft", color: "#8a8f98" },
  { status: "pending_approval", label: "Pending Approval", color: "#f59e0b" },
  { status: "approved", label: "Approved", color: "#3b82f6" },
  { status: "sent", label: "Sent", color: "#8b5cf6" },
  { status: "accepted", label: "Accepted", color: "#10b981" },
  { status: "rejected", label: "Rejected", color: "#ef4444" },
];

function offerTone(status: string): string {
  switch (status) {
    case "draft": return "slate";
    case "pending_approval": return "amber";
    case "approved": return "blue";
    case "sent": return "purple";
    case "accepted": return "emerald";
    case "rejected": return "red";
    default: return "slate";
  }
}

export default function OffersPage() {
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showDetail, setShowDetail] = useState<Offer | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [seekers, setSeekers] = useState<Seeker[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Form state
  const [formContractId, setFormContractId] = useState<number | "">("");
  const [formSeekerId, setFormSeekerId] = useState<number | "">("");
  const [formSalary, setFormSalary] = useState("");
  const [formCurrency, setFormCurrency] = useState("USD");
  const [formStartDate, setFormStartDate] = useState("");
  const [formExpiry, setFormExpiry] = useState("");
  const [formTerms, setFormTerms] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [approvalComment, setApprovalComment] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, c, s] = await Promise.all([
        api.offerPipeline(),
        api.contracts(),
        api.seekers(),
      ]);
      setPipeline(p);
      setContracts(c);
      setSeekers(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function createOffer(e: React.FormEvent) {
    e.preventDefault();
    setActionError(null);
    setSubmitting(true);
    try {
      await api.createOffer({
        contract_id: formContractId,
        seeker_id: formSeekerId,
        offered_salary: formSalary ? parseFloat(formSalary) : null,
        offered_currency: formCurrency,
        start_date: formStartDate || null,
        offer_expiry: formExpiry || null,
        terms: formTerms || null,
        notes: formNotes || null,
      });
      setShowCreate(false);
      resetForm();
      await load();
    } catch (e) {
      setActionError(e instanceof ApiError ? e.message : "Failed to create offer");
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setFormContractId("");
    setFormSeekerId("");
    setFormSalary("");
    setFormStartDate("");
    setFormExpiry("");
    setFormTerms("");
    setFormNotes("");
  }

  async function doAction(action: () => Promise<any>) {
    setActionError(null);
    try {
      await action();
      setShowDetail(null);
      await load();
    } catch (e) {
      setActionError(e instanceof ApiError ? e.message : "Action failed");
    }
  }

  async function deleteOffer(id: number) {
    if (!confirm("Delete this offer?")) return;
    await doAction(() => api.deleteOffer(id));
  }

  if (loading) return <Loading label="Loading offers..." />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  const allOffers = pipeline.reduce((acc: Offer[], col: any) => acc.concat(col.offers), []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Offer Management</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Track offers through the full lifecycle: draft, approval, send, and response.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow"
        >
          + Create Offer
        </button>
      </div>

      {allOffers.length === 0 ? (
        <EmptyState
          text="No offers yet. Create an offer to get started."
          action={
            <button onClick={() => setShowCreate(true)} className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium">
              + Create Offer
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-4">
          {pipeline.map((col: any) => (
            <div key={col.status} className="space-y-2">
              <div className="flex items-center gap-2 px-1 pb-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLUMNS.find(c => c.status === col.status)?.color || "#666" }} />
                <span className="text-xs font-semibold text-[#f7f8f8]">{col.label}</span>
                <span className="text-[10px] text-[#62666d] font-mono">({col.offers.length})</span>
              </div>
              <div className="space-y-2">
                {col.offers.map((o: Offer) => (
                  <div
                    key={o.id}
                    onClick={() => setShowDetail(o)}
                    className="linear-card p-3 bg-[#0f1011] cursor-pointer hover:bg-white/[0.02] transition"
                  >
                    <div className="flex items-start justify-between gap-1 mb-1.5">
                      <span className="text-[11px] font-semibold text-[#f7f8f8] leading-tight">
                        {o.seeker_name || `Seeker #${o.seeker_id}`}
                      </span>
                      <Badge tone={offerTone(o.status)}>{o.status.replace("_", " ")}</Badge>
                    </div>
                    <p className="text-[10px] text-[#8a8f98] mb-1.5">
                      {o.contract_title || `Contract #${o.contract_id}`}
                    </p>
                    {o.offered_salary != null ? (
                      <span className="px-1.5 py-0.5 rounded bg-white/[0.06] text-[10px] font-mono text-[#d0d6e0]">
                        {o.offered_currency} {o.offered_salary.toLocaleString()}
                      </span>
                    ) : null}
                    <p className="text-[9px] text-[#62666d] mt-1.5">
                      {new Date(o.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Offer" wide>
        <form onSubmit={createOffer} className="space-y-4">
          {actionError && (
            <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">{actionError}</div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-[11px] text-[#8a8f98] font-medium">Contract *</label>
              <select required value={formContractId} onChange={e => setFormContractId(Number(e.target.value))}
                className="linear-input w-full px-3 py-2 text-xs mt-1">
                <option value="">Select contract...</option>
                {contracts.map(c => (
                  <option key={c.id} value={c.id}>{c.title || `Contract #${c.id}`}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] text-[#8a8f98] font-medium">Candidate *</label>
              <select required value={formSeekerId} onChange={e => setFormSeekerId(Number(e.target.value))}
                className="linear-input w-full px-3 py-2 text-xs mt-1">
                <option value="">Select candidate...</option>
                {seekers.map(s => (
                  <option key={s.id} value={s.id}>{s.name || `Seeker #${s.id}`}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] text-[#8a8f98] font-medium">Salary</label>
              <input type="number" step="0.01" value={formSalary} onChange={e => setFormSalary(e.target.value)}
                className="linear-input w-full px-3 py-2 text-xs mt-1" placeholder="120000" />
            </div>
            <div>
              <label className="text-[11px] text-[#8a8f98] font-medium">Currency</label>
              <select value={formCurrency} onChange={e => setFormCurrency(e.target.value)}
                className="linear-input w-full px-3 py-2 text-xs mt-1">
                <option>USD</option><option>INR</option><option>EUR</option><option>GBP</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] text-[#8a8f98] font-medium">Start Date</label>
              <input type="date" value={formStartDate} onChange={e => setFormStartDate(e.target.value)}
                className="linear-input w-full px-3 py-2 text-xs mt-1" />
            </div>
          </div>
          <div>
            <label className="text-[11px] text-[#8a8f98] font-medium">Offer Expiry</label>
            <input type="date" value={formExpiry} onChange={e => setFormExpiry(e.target.value)}
              className="linear-input w-full px-3 py-2 text-xs mt-1" />
          </div>
          <div>
            <label className="text-[11px] text-[#8a8f98] font-medium">Terms & Conditions</label>
            <textarea rows={3} value={formTerms} onChange={e => setFormTerms(e.target.value)}
              className="linear-input w-full p-3 font-mono text-xs mt-1" placeholder="Bonus, equity, benefits..." />
          </div>
          <div>
            <label className="text-[11px] text-[#8a8f98] font-medium">Internal Notes</label>
            <textarea rows={2} value={formNotes} onChange={e => setFormNotes(e.target.value)}
              className="linear-input w-full p-3 font-mono text-xs mt-1" placeholder="Internal notes..." />
          </div>
          <div className="flex justify-end space-x-2 pt-3 border-t border-white/[0.08]">
            <button type="button" onClick={() => setShowCreate(false)}
              className="px-4 py-1.5 rounded bg-white/[0.08] text-white text-xs">Cancel</button>
            <button disabled={submitting}
              className="px-4 py-1.5 rounded bg-brand text-white text-xs disabled:opacity-50">
              {submitting ? "Creating..." : "Create Offer"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Detail Modal */}
      <Modal open={!!showDetail} onClose={() => { setShowDetail(null); setActionError(null); }} title="Offer Details" wide>
        {showDetail && (
          <div className="space-y-4">
            {actionError && (
              <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">{actionError}</div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Candidate</p>
                <p className="text-xs text-[#f7f8f8]">{showDetail.seeker_name || `Seeker #${showDetail.seeker_id}`}</p>
              </div>
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Contract</p>
                <p className="text-xs text-[#f7f8f8]">{showDetail.contract_title || `Contract #${showDetail.contract_id}`}</p>
              </div>
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Salary</p>
                <p className="text-xs font-mono text-[#f7f8f8]">
                  {showDetail.offered_salary != null ? `${showDetail.offered_currency} ${showDetail.offered_salary.toLocaleString()}` : "TBD"}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Status</p>
                <Badge tone={offerTone(showDetail.status)}>{showDetail.status.replace("_", " ")}</Badge>
              </div>
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Start Date</p>
                <p className="text-xs text-[#f7f8f8]">{showDetail.start_date || "TBD"}</p>
              </div>
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Expiry</p>
                <p className="text-xs text-[#f7f8f8]">{showDetail.offer_expiry || "None"}</p>
              </div>
            </div>
            {showDetail.terms && (
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Terms</p>
                <p className="text-xs text-[#d0d6e0] whitespace-pre-wrap">{showDetail.terms}</p>
              </div>
            )}
            {showDetail.notes && (
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Notes</p>
                <p className="text-xs text-[#d0d6e0] whitespace-pre-wrap">{showDetail.notes}</p>
              </div>
            )}
            {showDetail.approvals.length > 0 && (
              <div>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-2">Approval Chain</p>
                <div className="space-y-1.5">
                  {showDetail.approvals.map(a => (
                    <div key={a.id} className="flex items-center gap-2 text-xs">
                      <Badge tone={a.status === "approved" ? "emerald" : a.status === "rejected" ? "red" : "amber"}>
                        {a.status}
                      </Badge>
                      <span className="text-[#8a8f98]">{a.approver_name || `User #${a.approver_id}`}</span>
                      {a.comments && <span className="text-[#62666d]">- {a.comments}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {/* Timeline */}
            <div>
              <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-2">Timeline</p>
              <div className="space-y-1 text-[10px] text-[#8a8f98]">
                <div>Created: {new Date(showDetail.created_at).toLocaleString()}</div>
                {showDetail.approved_at && <div>Approved: {new Date(showDetail.approved_at).toLocaleString()}</div>}
                {showDetail.sent_at && <div>Sent: {new Date(showDetail.sent_at).toLocaleString()}</div>}
                {showDetail.responded_at && <div>Responded: {new Date(showDetail.responded_at).toLocaleString()}</div>}
              </div>
            </div>
            {/* Actions */}
            <div className="flex flex-wrap gap-2 pt-3 border-t border-white/[0.08]">
              {showDetail.status === "draft" && (
                <button onClick={() => doAction(() => api.submitOffer(showDetail.id))}
                  className="px-3 py-1.5 rounded bg-amber-500/20 text-amber-300 text-xs font-medium">
                  Submit for Approval
                </button>
              )}
              {showDetail.status === "pending_approval" && (
                <>
                  <button onClick={() => doAction(() => api.approveOffer(showDetail.id, approvalComment))}
                    className="px-3 py-1.5 rounded bg-emerald-500/20 text-emerald-300 text-xs font-medium">
                    Approve
                  </button>
                  <button onClick={() => doAction(() => api.rejectOffer(showDetail.id, approvalComment))}
                    className="px-3 py-1.5 rounded bg-red-500/20 text-red-300 text-xs font-medium">
                    Reject
                  </button>
                  <input value={approvalComment} onChange={e => setApprovalComment(e.target.value)}
                    className="linear-input px-2 py-1 text-[10px] flex-1" placeholder="Comments (optional)" />
                </>
              )}
              {showDetail.status === "approved" && (
                <button onClick={() => doAction(() => api.sendOffer(showDetail.id))}
                  className="px-3 py-1.5 rounded bg-purple-500/20 text-purple-300 text-xs font-medium">
                  Send to Candidate
                </button>
              )}
              {showDetail.status === "sent" && (
                <>
                  <button onClick={() => doAction(() => api.acceptOffer(showDetail.id))}
                    className="px-3 py-1.5 rounded bg-emerald-500/20 text-emerald-300 text-xs font-medium">
                    Mark Accepted
                  </button>
                  <button onClick={() => doAction(() => api.rejectOffer(showDetail.id))}
                    className="px-3 py-1.5 rounded bg-red-500/20 text-red-300 text-xs font-medium">
                    Mark Rejected
                  </button>
                </>
              )}
              {["draft", "pending_approval", "approved"].includes(showDetail.status) && (
                <button onClick={() => doAction(() => api.withdrawOffer(showDetail.id))}
                  className="px-3 py-1.5 rounded bg-white/[0.06] text-[#8a8f98] text-xs">
                  Withdraw
                </button>
              )}
              {["draft"].includes(showDetail.status) && (
                <button onClick={() => deleteOffer(showDetail.id)}
                  className="px-3 py-1.5 rounded bg-red-500/10 text-red-400 text-xs">
                  Delete
                </button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
