"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api, ApiError } from "@/lib/client";
import type { Contract, MarketIntelligence, ScreeningResult } from "@/lib/types";

export default function AIScreeningPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<number | "">("");
  const [screening, setScreening] = useState(false);
  const [results, setResults] = useState<ScreeningResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Skills extraction
  const [extractText, setExtractText] = useState("");
  const [extractedSkills, setExtractedSkills] = useState<string[]>([]);
  const [extracting, setExtracting] = useState(false);

  // Market intelligence
  const [intelTitle, setIntelTitle] = useState("");
  const [intelSkills, setIntelSkills] = useState("");
  const [intelLocation, setIntelLocation] = useState("");
  const [intelResult, setIntelResult] = useState<MarketIntelligence | null>(null);
  const [intelLoading, setIntelLoading] = useState(false);

  // Skills taxonomy
  const [taxonomy, setTaxonomy] = useState<Record<string, string[]> | null>(null);
  const [showTaxonomy, setShowTaxonomy] = useState(false);

  // Drag and drop
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.contracts().then(setContracts).catch(() => {}).finally(() => setLoading(false));
  }, []);

  function onDrag(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files).filter(f =>
      f.name.endsWith(".pdf") || f.name.endsWith(".doc") || f.name.endsWith(".docx") || f.name.endsWith(".txt")
    );
    if (files.length) setUploadedFiles(prev => [...prev, ...files]);
  }

  function onFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    setUploadedFiles(prev => [...prev, ...files]);
  }

  async function runScreening() {
    if (!selectedContract) return;
    setScreening(true);
    setError(null);
    setResults([]);
    try {
      const res = await api.aiScreen(Number(selectedContract));
      setResults(res.results);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Screening failed");
    } finally {
      setScreening(false);
    }
  }

  async function extractSkills() {
    if (!extractText.trim()) return;
    setExtracting(true);
    try {
      const res = await api.aiSkillsExtract(extractText);
      setExtractedSkills(res.skills);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Extraction failed");
    } finally {
      setExtracting(false);
    }
  }

  async function fetchMarketIntel() {
    if (!intelTitle.trim()) return;
    setIntelLoading(true);
    try {
      const skills = intelSkills.split(",").map(s => s.trim()).filter(Boolean);
      const res = await api.aiMarketIntel(intelTitle, skills, intelLocation || undefined);
      setIntelResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Market intel failed");
    } finally {
      setIntelLoading(false);
    }
  }

  async function loadTaxonomy() {
    try {
      const res = await api.aiSkillsTaxonomy();
      setTaxonomy(res.categories);
      setShowTaxonomy(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Taxonomy load failed");
    }
  }

  function tierColor(tier: string) {
    if (tier === "A") return "emerald";
    if (tier === "B") return "amber";
    return "red";
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Resume Screening</h1>
        <p className="text-xs text-[#8a8f98] mt-1">
          Batch screen candidates, extract skills, and get market intelligence powered by AI.
        </p>
      </div>

      {error && <ErrorBanner message={error} onRetry={() => setError(null)} />}

      {/* Batch Screening Section */}
      <div className="linear-card p-5 bg-[#0f1011] space-y-4">
        <h2 className="text-sm font-semibold text-[#f7f8f8]">Batch Resume Screening</h2>
        <p className="text-[11px] text-[#8a8f98]">Select a target contract to score all active candidates against it.</p>

        <div className="flex flex-col md:flex-row gap-3">
          <select value={selectedContract} onChange={e => setSelectedContract(Number(e.target.value) || "")}
            className="linear-input px-3 py-2 text-xs flex-1">
            <option value="">Select target contract...</option>
            {contracts.map(c => (
              <option key={c.id} value={c.id}>{c.title || `Contract #${c.id}`} - {c.client_name || "Direct"}</option>
            ))}
          </select>
          <button onClick={runScreening} disabled={!selectedContract || screening}
            className="px-4 py-2 rounded bg-brand text-white text-xs font-medium disabled:opacity-50 whitespace-nowrap">
            {screening ? "Screening..." : "Run AI Screening"}
          </button>
        </div>

        {/* Drag & Drop Zone */}
        <div
          onDragEnter={onDrag} onDragLeave={onDrag} onDragOver={onDrag} onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition ${
            dragActive ? "border-brand bg-brand/5" : "border-white/10 hover:border-white/20"
          }`}
        >
          <input ref={inputRef} type="file" multiple accept=".pdf,.doc,.docx,.txt"
            onChange={onFileSelect} className="hidden" />
          <p className="text-xs text-[#8a8f98]">
            Drag & drop resumes here (PDF, DOC, TXT) or click to browse
          </p>
          {uploadedFiles.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1 justify-center">
              {uploadedFiles.map((f, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-white/[0.06] text-[10px] text-[#d0d6e0]">
                  {f.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Screening Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-[#f7f8f8]">Screening Results ({results.length} candidates)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {results.map(r => (
              <div key={r.seeker_id} className="linear-card p-4 bg-[#0f1011] space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold text-[#f7f8f8]">{r.seeker_name || `Seeker #${r.seeker_id}`}</p>
                    <p className="text-[10px] text-[#8a8f98]">{r.seeker_headline || ""}</p>
                  </div>
                  <Badge tone={tierColor(r.tier)}>{r.tier}</Badge>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="flex justify-between text-[10px] text-[#8a8f98] mb-1">
                      <span>Overall</span>
                      <span className="text-[#f7f8f8] font-mono">{r.overall_score}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-brand" style={{ width: `${r.overall_score}%` }} />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between text-[10px] text-[#8a8f98] mb-1">
                      <span>Skill Coverage</span>
                      <span className="text-[#f7f8f8] font-mono">{r.skill_coverage}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${r.skill_coverage}%` }} />
                    </div>
                  </div>
                </div>
                {r.matched_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {r.matched_skills.map(s => (
                      <span key={s} className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[9px]">{s}</span>
                    ))}
                  </div>
                )}
                {r.missing_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {r.missing_skills.map(s => (
                      <span key={s} className="px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 text-[9px]">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Skills Extraction */}
      <div className="linear-card p-5 bg-[#0f1011] space-y-4">
        <h2 className="text-sm font-semibold text-[#f7f8f8]">Skills Extraction</h2>
        <p className="text-[11px] text-[#8a8f98]">Paste resume text or job description to extract skills.</p>
        <textarea rows={4} value={extractText} onChange={e => setExtractText(e.target.value)}
          className="linear-input w-full p-3 font-mono text-xs"
          placeholder="Paste resume or job description text here..." />
        <div className="flex items-center gap-3">
          <button onClick={extractSkills} disabled={!extractText.trim() || extracting}
            className="px-4 py-2 rounded bg-brand text-white text-xs font-medium disabled:opacity-50">
            {extracting ? "Extracting..." : "Extract Skills"}
          </button>
          <button onClick={loadTaxonomy}
            className="px-4 py-2 rounded bg-white/[0.06] text-[#d0d6e0] text-xs font-medium">
            View Skills Taxonomy
          </button>
        </div>
        {extractedSkills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-2 border-t border-white/[0.06]">
            {extractedSkills.map(s => (
              <span key={s} className="px-2 py-0.5 rounded bg-brand/10 text-brand-light text-[10px]">{s}</span>
            ))}
          </div>
        )}
      </div>

      {/* Skills Taxonomy Modal */}
      {showTaxonomy && taxonomy && (
        <div className="linear-card p-5 bg-[#0f1011] space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#f7f8f8]">Skills Taxonomy</h2>
            <button onClick={() => setShowTaxonomy(false)} className="text-[#8a8f98] hover:text-white text-xs">Close</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 max-h-96 overflow-y-auto">
            {Object.entries(taxonomy).map(([cat, skills]) => (
              <div key={cat}>
                <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1.5 font-mono">{cat.replace(/_/g, " ")}</p>
                <div className="flex flex-wrap gap-1">
                  {skills.map(s => (
                    <span key={s} className="px-1.5 py-0.5 rounded bg-white/[0.06] text-[9px] text-[#d0d6e0]">{s}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Market Intelligence */}
      <div className="linear-card p-5 bg-[#0f1011] space-y-4">
        <h2 className="text-sm font-semibold text-[#f7f8f8]">Market Intelligence</h2>
        <p className="text-[11px] text-[#8a8f98]">Get salary ranges, demand levels, and competition data for a role.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input value={intelTitle} onChange={e => setIntelTitle(e.target.value)}
            className="linear-input px-3 py-2 text-xs" placeholder="Job title (e.g. Senior React Developer)" />
          <input value={intelSkills} onChange={e => setIntelSkills(e.target.value)}
            className="linear-input px-3 py-2 text-xs" placeholder="Skills (comma-separated)" />
          <input value={intelLocation} onChange={e => setIntelLocation(e.target.value)}
            className="linear-input px-3 py-2 text-xs" placeholder="Location (optional)" />
        </div>
        <button onClick={fetchMarketIntel} disabled={!intelTitle.trim() || intelLoading}
          className="px-4 py-2 rounded bg-brand text-white text-xs font-medium disabled:opacity-50">
          {intelLoading ? "Fetching..." : "Get Market Intelligence"}
        </button>
        {intelResult && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-3 border-t border-white/[0.06]">
            <div>
              <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Salary Range</p>
              <p className="text-xs font-mono text-[#f7f8f8]">
                {intelResult.salary_range.currency} {intelResult.salary_range.min.toLocaleString()} - {intelResult.salary_range.max.toLocaleString()}
              </p>
              <p className="text-[10px] text-[#8a8f98]">Median: {intelResult.salary_range.currency} {intelResult.salary_range.median.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Demand Level</p>
              <Badge tone={intelResult.demand_level === "high" ? "emerald" : intelResult.demand_level === "medium" ? "amber" : "red"}>
                {intelResult.demand_level}
              </Badge>
            </div>
            <div>
              <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Competition</p>
              <Badge tone={intelResult.competition_level === "high" ? "red" : intelResult.competition_level === "medium" ? "amber" : "emerald"}>
                {intelResult.competition_level}
              </Badge>
            </div>
            <div>
              <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Top Locations</p>
              <p className="text-[10px] text-[#d0d6e0]">{intelResult.top_locations.join(", ")}</p>
            </div>
          </div>
        )}
        {intelResult && (
          <div className="pt-3 border-t border-white/[0.06]">
            <p className="text-[10px] text-[#62666d] uppercase tracking-wider mb-1">Trending Skills</p>
            <div className="flex flex-wrap gap-1">
              {intelResult.trending_skills.map(s => (
                <span key={s} className="px-2 py-0.5 rounded bg-brand/10 text-brand-light text-[10px]">{s}</span>
              ))}
            </div>
            <p className="text-[11px] text-[#8a8f98] mt-2">{intelResult.market_notes}</p>
          </div>
        )}
      </div>
    </div>
  );
}
