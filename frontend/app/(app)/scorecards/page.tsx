"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading, Modal } from "@/components/UI";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/client";
import type { Scorecard, ScorecardTemplate, ScorecardSummary } from "@/lib/types";

const RECOMMENDATIONS = [
  { value: "strong_hire", label: "Strong Hire", color: "text-emerald-400" },
  { value: "hire", label: "Hire", color: "text-emerald-300" },
  { value: "neutral", label: "Neutral", color: "text-[#8a8f98]" },
  { value: "no_hire", label: "No Hire", color: "text-amber-400" },
  { value: "strong_no_hire", label: "Strong No Hire", color: "text-red-400" },
];

function RadarChart({ averages }: { averages: { criterion: string; avg_score: number; count: number }[] }) {
  if (averages.length === 0) return null;
  const maxScore = 5;
  const cx = 100;
  const cy = 100;
  const r = 80;
  const n = averages.length;
  const angleStep = (2 * Math.PI) / n;

  const getPoint = (i: number, val: number) => {
    const angle = i * angleStep - Math.PI / 2;
    const dist = (val / maxScore) * r;
    return { x: cx + dist * Math.cos(angle), y: cy + dist * Math.sin(angle) };
  };

  const dataPoints = averages.map((a, i) => getPoint(i, a.avg_score));
  const gridLevels = [1, 2, 3, 4, 5];

  return (
    <svg viewBox="0 0 200 200" className="w-full max-w-xs mx-auto">
      {gridLevels.map((level) => {
        const pts = averages.map((_, i) => getPoint(i, level));
        const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
        return <path key={level} d={d} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />;
      })}
      {averages.map((_, i) => {
        const p = getPoint(i, maxScore);
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />;
      })}
      <polygon
        points={dataPoints.map((p) => `${p.x},${p.y}`).join(" ")}
        fill="rgba(94,106,210,0.2)"
        stroke="rgba(94,106,210,0.6)"
        strokeWidth="1.5"
      />
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#5e6ad2" />
      ))}
      {averages.map((a, i) => {
        const angle = i * angleStep - Math.PI / 2;
        const labelDist = r + 18;
        const lx = cx + labelDist * Math.cos(angle);
        const ly = cy + labelDist * Math.sin(angle);
        return (
          <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" className="fill-[#8a8f98]" fontSize="7">
            {a.criterion}
          </text>
        );
      })}
    </svg>
  );
}

export default function ScorecardsPage() {
  const { toast } = useToast();
  const [view, setView] = useState<"templates" | "scorecards">("scorecards");
  const [templates, setTemplates] = useState<ScorecardTemplate[]>([]);
  const [scorecards, setScorecards] = useState<Scorecard[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [editTemplate, setEditTemplate] = useState<ScorecardTemplate | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [templateCriteria, setTemplateCriteria] = useState<
    { name: string; weight: number; description: string; scale_max: number }[]
  >([{ name: "", weight: 1, description: "", scale_max: 5 }]);

  const [showScorecardModal, setShowScorecardModal] = useState(false);
  const [editScorecard, setEditScorecard] = useState<Scorecard | null>(null);
  const [scInterviewId, setScInterviewId] = useState("");
  const [scTemplateId, setScTemplateId] = useState("");
  const [scScores, setScScores] = useState<{ criterion: string; score: number; notes: string }[]>([]);
  const [scRecommendation, setScRecommendation] = useState("");
  const [scNotes, setScNotes] = useState("");

  const [summaryInterviewId, setSummaryInterviewId] = useState("");
  const [summary, setSummary] = useState<ScorecardSummary | null>(null);
  const [showSummary, setShowSummary] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [t, s] = await Promise.all([api.scorecardTemplates(), api.scorecards()]);
      setTemplates(t);
      setScorecards(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load scorecards");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function openCreateTemplate() {
    setEditTemplate(null);
    setTemplateName("");
    setTemplateCriteria([{ name: "", weight: 1, description: "", scale_max: 5 }]);
    setShowTemplateModal(true);
  }

  function openEditTemplate(t: ScorecardTemplate) {
    setEditTemplate(t);
    setTemplateName(t.name);
    setTemplateCriteria([...t.criteria]);
    setShowTemplateModal(true);
  }

  async function saveTemplate() {
    const payload = { name: templateName, criteria: templateCriteria };
    try {
      if (editTemplate) {
        await api.updateScorecardTemplate(editTemplate.id, payload);
      } else {
        await api.createScorecardTemplate(payload);
      }
      toast("success", "Template saved");
      setShowTemplateModal(false);
      load();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Failed to save");
    }
  }

  async function deleteTemplate(id: number) {
    try {
      await api.deleteScorecardTemplate(id);
      toast("success", "Template deleted");
      load();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Failed to delete");
    }
  }

  function openCreateScorecard() {
    setEditScorecard(null);
    setScInterviewId("");
    setScTemplateId(templates[0]?.id?.toString() ?? "");
    setScScores([]);
    setScRecommendation("");
    setScNotes("");
    setShowScorecardModal(true);
  }

  function openEditScorecard(s: Scorecard) {
    setEditScorecard(s);
    setScInterviewId(s.interview_id.toString());
    setScTemplateId(s.template_id.toString());
    setScScores([...s.scores]);
    setScRecommendation(s.recommendation ?? "");
    setScNotes(s.notes ?? "");
    setShowScorecardModal(true);
  }

  async function saveScorecard() {
    const overall =
      scScores.length > 0 ? scScores.reduce((sum, s) => sum + s.score, 0) / scScores.length : 0;
    const payload = {
      interview_id: Number(scInterviewId),
      template_id: Number(scTemplateId),
      scores: scScores,
      overall_score: Math.round(overall * 10) / 10,
      recommendation: scRecommendation || null,
      notes: scNotes || null,
    };
    try {
      if (editScorecard) {
        await api.updateScorecard(editScorecard.id, payload);
      } else {
        await api.createScorecard(payload);
      }
      toast("success", "Scorecard saved");
      setShowScorecardModal(false);
      load();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Failed to save");
    }
  }

  async function deleteScorecard(id: number) {
    try {
      await api.deleteScorecard(id);
      toast("success", "Scorecard deleted");
      load();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Failed to delete");
    }
  }

  async function loadSummary() {
    if (!summaryInterviewId) return;
    try {
      const s = await api.scorecardSummary(Number(summaryInterviewId));
      setSummary(s);
      setShowSummary(true);
    } catch {
      setError("No scorecards found for this interview");
    }
  }

  function initScorecardFromTemplate(templateId: number) {
    const t = templates.find((t) => t.id === templateId);
    if (t) {
      setScScores(t.criteria.map((c) => ({ criterion: c.name, score: 0, notes: "" })));
    }
  }

  function recColor(rec: string | null) {
    return RECOMMENDATIONS.find((r) => r.value === rec)?.color ?? "text-[#8a8f98]";
  }

  function recLabel(rec: string | null) {
    return RECOMMENDATIONS.find((r) => r.value === rec)?.label ?? rec ?? "\u2014";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Candidate Scorecards</h1>
          <p className="text-xs text-[#8a8f98] mt-1">
            Structured interview evaluation with criteria-based scoring.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="number"
            placeholder="Interview ID"
            value={summaryInterviewId}
            onChange={(e) => setSummaryInterviewId(e.target.value)}
            className="w-28 bg-white/[0.06] border border-white/10 rounded px-2 py-1 text-xs text-[#f7f8f8]"
          />
          <button
            onClick={loadSummary}
            className="px-3 py-1.5 rounded bg-white/[0.06] border border-white/10 text-xs text-[#8a8f98] hover:text-white transition"
          >
            Summary
          </button>
        </div>
      </div>

      <div className="flex space-x-1 border-b border-white/[0.08] pb-1">
        <button
          onClick={() => setView("scorecards")}
          className={`px-3 py-1.5 text-xs font-medium rounded transition ${
            view === "scorecards"
              ? "bg-brand/20 text-brand-light"
              : "text-[#8a8f98] hover:text-white"
          }`}
        >
          Scorecards
        </button>
        <button
          onClick={() => setView("templates")}
          className={`px-3 py-1.5 text-xs font-medium rounded transition ${
            view === "templates"
              ? "bg-brand/20 text-brand-light"
              : "text-[#8a8f98] hover:text-white"
          }`}
        >
          Templates
        </button>
      </div>

      {loading ? (
        <Loading label="Loading scorecards\u2026" />
      ) : error ? (
        <ErrorBanner message={error} onRetry={load} />
      ) : view === "templates" ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={openCreateTemplate}
              className="px-3 py-1.5 rounded bg-brand/20 hover:bg-brand/30 text-brand-light text-xs font-medium transition"
            >
              + New Template
            </button>
          </div>
          {templates.length === 0 ? (
            <EmptyState text="No templates yet. Create one to get started." />
          ) : (
            <div className="space-y-3">
              {templates.map((t) => (
                <div key={t.id} className="linear-card p-4 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-[#f7f8f8]">{t.name}</div>
                    <div className="text-[11px] text-[#8a8f98] mt-1">
                      {t.criteria.length} criteria \u00b7 {t.is_default ? "Default" : "Custom"}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => openEditTemplate(t)}
                      className="text-xs text-brand-light hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deleteTemplate(t.id)}
                      className="text-xs text-red-400 hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={openCreateScorecard}
              className="px-3 py-1.5 rounded bg-brand/20 hover:bg-brand/30 text-brand-light text-xs font-medium transition"
            >
              + New Scorecard
            </button>
          </div>
          {scorecards.length === 0 ? (
            <EmptyState text="No scorecards yet. Fill one for an interview." />
          ) : (
            <div className="linear-card p-5 space-y-3">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
                      <th className="py-2.5 px-3">Interview</th>
                      <th className="py-2.5 px-3">Evaluator</th>
                      <th className="py-2.5 px-3">Overall</th>
                      <th className="py-2.5 px-3">Recommendation</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
                    {scorecards.map((s) => (
                      <tr key={s.id} className="hover:bg-white/[0.02]">
                        <td className="py-3 px-3 font-mono">#{s.interview_id}</td>
                        <td className="py-3 px-3">{s.evaluator_id}</td>
                        <td className="py-3 px-3">
                          <span className="font-mono font-bold text-[#f7f8f8]">
                            {s.overall_score}
                          </span>
                          <span className="text-[10px] text-[#8a8f98] ml-1">/ 5</span>
                        </td>
                        <td className="py-3 px-3">
                          <span className={`font-medium ${recColor(s.recommendation)}`}>
                            {recLabel(s.recommendation)}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-[#8a8f98] font-mono">
                          {s.created_at
                            ? new Date(s.created_at).toLocaleDateString()
                            : "\u2014"}
                        </td>
                        <td className="py-3 px-3 space-x-2">
                          <button
                            onClick={() => openEditScorecard(s)}
                            className="text-brand-light hover:underline"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => deleteScorecard(s.id)}
                            className="text-red-400 hover:underline"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <Modal
        open={showTemplateModal}
        title={editTemplate ? "Edit Template" : "New Template"}
        onClose={() => setShowTemplateModal(false)}
        wide
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-[#8a8f98] mb-1">Template Name</label>
            <input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="w-full bg-white/[0.06] border border-white/10 rounded px-3 py-2 text-sm text-[#f7f8f8]"
              placeholder="e.g. Technical Interview"
            />
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs text-[#8a8f98]">Criteria</label>
              <button
                onClick={() =>
                  setTemplateCriteria([
                    ...templateCriteria,
                    { name: "", weight: 1, description: "", scale_max: 5 },
                  ])
                }
                className="text-xs text-brand-light hover:underline"
              >
                + Add Criterion
              </button>
            </div>
            {templateCriteria.map((c, i) => (
              <div
                key={i}
                className="p-3 rounded bg-white/[0.02] border border-white/[0.06] space-y-2"
              >
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={c.name}
                    onChange={(e) => {
                      const next = [...templateCriteria];
                      next[i] = { ...next[i], name: e.target.value };
                      setTemplateCriteria(next);
                    }}
                    className="flex-1 bg-white/[0.06] border border-white/10 rounded px-2 py-1 text-xs text-[#f7f8f8]"
                    placeholder="Criterion name"
                  />
                  <input
                    type="number"
                    value={c.weight}
                    onChange={(e) => {
                      const next = [...templateCriteria];
                      next[i] = { ...next[i], weight: Number(e.target.value) };
                      setTemplateCriteria(next);
                    }}
                    className="w-16 bg-white/[0.06] border border-white/10 rounded px-2 py-1 text-xs text-[#f7f8f8] text-center"
                    placeholder="Weight"
                  />
                  <button
                    onClick={() => setTemplateCriteria(templateCriteria.filter((_, j) => j !== i))}
                    className="text-red-400 text-xs hover:underline"
                  >
                    Remove
                  </button>
                </div>
                <input
                  type="text"
                  value={c.description}
                  onChange={(e) => {
                    const next = [...templateCriteria];
                    next[i] = { ...next[i], description: e.target.value };
                    setTemplateCriteria(next);
                  }}
                  className="w-full bg-white/[0.06] border border-white/10 rounded px-2 py-1 text-xs text-[#f7f8f8]"
                  placeholder="Description (optional)"
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end space-x-2">
            <button
              onClick={() => setShowTemplateModal(false)}
              className="px-3 py-1.5 rounded border border-white/10 text-xs text-[#8a8f98] hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={saveTemplate}
              className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium hover:bg-brand-hover transition"
            >
              {editTemplate ? "Update" : "Create"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={showScorecardModal}
        title={editScorecard ? "Edit Scorecard" : "New Scorecard"}
        onClose={() => setShowScorecardModal(false)}
        wide
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-[#8a8f98] mb-1">Interview ID</label>
              <input
                type="number"
                value={scInterviewId}
                onChange={(e) => setScInterviewId(e.target.value)}
                className="w-full bg-white/[0.06] border border-white/10 rounded px-3 py-2 text-sm text-[#f7f8f8]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8a8f98] mb-1">Template</label>
              <select
                value={scTemplateId}
                onChange={(e) => {
                  setScTemplateId(e.target.value);
                  initScorecardFromTemplate(Number(e.target.value));
                }}
                className="w-full bg-white/[0.06] border border-white/10 rounded px-3 py-2 text-sm text-[#f7f8f8]"
              >
                <option value="">Select template</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-3">
            <label className="text-xs text-[#8a8f98]">Scores</label>
            {scScores.map((s, i) => (
              <div
                key={i}
                className="p-3 rounded bg-white/[0.02] border border-white/[0.06] space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-[#f7f8f8]">{s.criterion}</span>
                  <div className="flex items-center space-x-1">
                    {[1, 2, 3, 4, 5].map((v) => (
                      <button
                        key={v}
                        onClick={() => {
                          const next = [...scScores];
                          next[i] = { ...next[i], score: v };
                          setScScores(next);
                        }}
                        className={`w-7 h-7 rounded text-[10px] font-mono transition ${
                          s.score === v
                            ? "bg-brand text-white"
                            : "bg-white/[0.06] text-[#8a8f98] hover:bg-white/[0.1]"
                        }`}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  type="text"
                  value={s.notes}
                  onChange={(e) => {
                    const next = [...scScores];
                    next[i] = { ...next[i], notes: e.target.value };
                    setScScores(next);
                  }}
                  className="w-full bg-white/[0.06] border border-white/10 rounded px-2 py-1 text-xs text-[#f7f8f8]"
                  placeholder="Notes (optional)"
                />
              </div>
            ))}
          </div>
          <div>
            <label className="block text-xs text-[#8a8f98] mb-1">Recommendation</label>
            <div className="flex space-x-2">
              {RECOMMENDATIONS.map((r) => (
                <button
                  key={r.value}
                  onClick={() => setScRecommendation(r.value)}
                  className={`px-3 py-1.5 rounded border text-xs transition ${
                    scRecommendation === r.value
                      ? "border-brand bg-brand/20 text-brand-light"
                      : "border-white/10 text-[#8a8f98] hover:text-white"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs text-[#8a8f98] mb-1">Notes</label>
            <textarea
              value={scNotes}
              onChange={(e) => setScNotes(e.target.value)}
              rows={3}
              className="w-full bg-white/[0.06] border border-white/10 rounded px-3 py-2 text-sm text-[#f7f8f8]"
              placeholder="Overall notes about the candidate..."
            />
          </div>
          <div className="flex justify-end space-x-2">
            <button
              onClick={() => setShowScorecardModal(false)}
              className="px-3 py-1.5 rounded border border-white/10 text-xs text-[#8a8f98] hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={saveScorecard}
              className="px-3 py-1.5 rounded bg-brand text-white text-xs font-medium hover:bg-brand-hover transition"
            >
              {editScorecard ? "Update" : "Save"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={showSummary}
        title="Scorecard Summary"
        onClose={() => setShowSummary(false)}
        wide
      >
        {summary && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="linear-card p-3 text-center">
                <div className="text-[11px] text-[#8a8f98]">Total Scorecards</div>
                <div className="text-xl font-semibold text-[#f7f8f8]">
                  {summary.total_scorecards}
                </div>
              </div>
              <div className="linear-card p-3 text-center">
                <div className="text-[11px] text-[#8a8f98]">Avg Overall Score</div>
                <div className="text-xl font-semibold text-[#f7f8f8]">
                  {summary.avg_overall}
                </div>
              </div>
              <div className="linear-card p-3 text-center">
                <div className="text-[11px] text-[#8a8f98]">Recommendations</div>
                <div className="space-y-1 mt-1">
                  {Object.entries(summary.recommendations).map(([rec, count]) => (
                    <div key={rec} className={`text-xs font-mono ${recColor(rec)}`}>
                      {recLabel(rec)}: {count}
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="linear-card p-5">
              <h3 className="text-sm font-semibold mb-3">Radar Chart</h3>
              <RadarChart averages={summary.criterion_averages} />
            </div>
            <div className="linear-card p-5 space-y-3">
              <h3 className="text-sm font-semibold">Criterion Averages</h3>
              {summary.criterion_averages.map((c) => (
                <div key={c.criterion} className="flex items-center space-x-3">
                  <span className="w-32 text-xs text-[#8a8f98] text-right">{c.criterion}</span>
                  <div className="flex-1 bg-white/[0.04] h-4 rounded overflow-hidden">
                    <div
                      className="h-full bg-brand/60 rounded flex items-center justify-end pr-2"
                      style={{ width: `${(c.avg_score / 5) * 100}%` }}
                    >
                      <span className="text-[10px] font-mono text-white/80">{c.avg_score}</span>
                    </div>
                  </div>
                  <span className="text-[10px] text-[#62666d] font-mono">{c.count} evals</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
