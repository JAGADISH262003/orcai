"use client";

import { useState } from "react";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api, pollJob } from "@/lib/client";
import type { Job } from "@/lib/types";

type Source = "google" | "rss" | "indeed" | "naukri" | "custom_url" | "github" | "stackoverflow" | "linkedin";

const JOB_SOURCES: { value: Source; label: string; needsUrl?: boolean; needsFeed?: boolean }[] = [
  { value: "google", label: "Google Custom Search" },
  { value: "rss", label: "RSS/Atom Feed", needsFeed: true },
  { value: "indeed", label: "Indeed" },
  { value: "naukri", label: "Naukri" },
  { value: "custom_url", label: "Custom URL", needsUrl: true },
];

const CANDIDATE_SOURCES: { value: Source; label: string; needsUrl?: boolean; needsFeed?: boolean }[] = [
  { value: "google", label: "Google Profiles" },
  { value: "github", label: "GitHub Users" },
  { value: "stackoverflow", label: "StackOverflow" },
  { value: "linkedin", label: "LinkedIn (via Google)" },
  { value: "custom_url", label: "Custom URL", needsUrl: true },
];

export default function ScrapersPage() {
  const [tab, setTab] = useState<"jobs" | "candidates">("jobs");
  const [source, setSource] = useState<Source>("google");
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [url, setUrl] = useState("");
  const [feedUrl, setFeedUrl] = useState("");
  const [maxResults, setMaxResults] = useState(25);
  const [country, setCountry] = useState("us");
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [asyncJob, setAsyncJob] = useState<Job | null>(null);

  const sources = tab === "jobs" ? JOB_SOURCES : CANDIDATE_SOURCES;
  const selected = sources.find((s) => s.value === source);

  async function handleScrape(async_: boolean) {
    setLoading(true);
    setError(null);
    setResults([]);
    setAsyncJob(null);
    try {
      const params: Record<string, unknown> = { source, query, location: location || undefined, max_results: maxResults, async: async_ };
      if (tab === "jobs") {
        params.country = country;
        if (url) params.url = url;
        if (feedUrl) params.feed_url = feedUrl;
        const res = await api.scrapeJobs(params);
        if (async_ && (res as unknown as Job).id) {
          setAsyncJob(res as unknown as Job);
          const final = await pollJob((res as unknown as Job).id);
          const r = final.result as Record<string, unknown> | undefined;
          setResults((r?.jobs as Record<string, unknown>[]) || []);
        } else {
          const r = res as unknown as Record<string, unknown>;
          setResults((r.jobs as Record<string, unknown>[]) || []);
        }
      } else {
        if (url) params.url = url;
        const res = await api.scrapeCandidates(params);
        if (async_ && (res as unknown as Job).id) {
          setAsyncJob(res as unknown as Job);
          const final = await pollJob((res as unknown as Job).id);
          const r = final.result as Record<string, unknown> | undefined;
          setResults((r?.candidates as Record<string, unknown>[]) || []);
        } else {
          const r = res as unknown as Record<string, unknown>;
          setResults((r.candidates as Record<string, unknown>[]) || []);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scrape failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Job & Candidate Scrapers</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Search external sources for job postings and candidate profiles.</p>
      </div>

      <div className="flex gap-2 border-b border-white/[0.06] pb-2">
        {(["jobs", "candidates"] as const).map((t) => (
          <button
            key={t}
            className={`px-3 py-1 text-xs font-medium rounded transition ${tab === t ? "bg-[#5e6ad2] text-white" : "text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-white/[0.04]"}`}
            onClick={() => { setTab(t); setSource("google"); setResults([]); }}
          >
            {t === "jobs" ? "Job Search" : "Candidate Search"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Source</label>
          <select className="linear-input w-full px-3 py-1.5 text-xs" value={source} onChange={(e) => setSource(e.target.value as Source)}>
            {sources.map((s) => (<option key={s.value} value={s.value}>{s.label}</option>))}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Query</label>
          <input className="linear-input w-full px-3 py-1.5 text-xs" placeholder={tab === "jobs" ? "e.g. senior python developer" : "e.g. john react developer"} value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div>
          <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Location</label>
          <input className="linear-input w-full px-3 py-1.5 text-xs" placeholder="e.g. Bangalore, India" value={location} onChange={(e) => setLocation(e.target.value)} />
        </div>
        {selected?.needsUrl && (
          <div>
            <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">URL</label>
            <input className="linear-input w-full px-3 py-1.5 text-xs" placeholder="https://..." value={url} onChange={(e) => setUrl(e.target.value)} />
          </div>
        )}
        {selected?.needsFeed && (
          <div>
            <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Feed URL</label>
            <input className="linear-input w-full px-3 py-1.5 text-xs" placeholder="https://...rss" value={feedUrl} onChange={(e) => setFeedUrl(e.target.value)} />
          </div>
        )}
        {tab === "jobs" && (
          <div>
            <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Country</label>
            <select className="linear-input w-full px-3 py-1.5 text-xs" value={country} onChange={(e) => setCountry(e.target.value)}>
              <option value="us">US</option>
              <option value="in">India</option>
              <option value="uk">UK</option>
              <option value="ca">Canada</option>
            </select>
          </div>
        )}
        <div>
          <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Max Results</label>
          <input type="number" className="linear-input w-full px-3 py-1.5 text-xs" value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))} min={1} max={100} />
        </div>
      </div>

      <div className="flex gap-3">
        <button className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow disabled:opacity-50" onClick={() => handleScrape(false)} disabled={loading || !query}>Run Now</button>
        <button className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50" onClick={() => handleScrape(true)} disabled={loading || !query}>Run Background</button>
      </div>

      {asyncJob && (
        <div className="linear-card p-3 text-xs text-[#d0d6e0]">
          Job #{asyncJob.id} — status: <span className="font-mono text-[#8a8f98]">{asyncJob.status}</span>
          {asyncJob.status === "done" && <span className="text-green-400 ml-2">Done</span>}
          {asyncJob.status === "failed" && <span className="text-red-400 ml-2">Failed</span>}
        </div>
      )}

      {error && <ErrorBanner message={error} />}
      {loading && <Loading label="Scraping..." />}

      {!loading && results.length > 0 && (
        <div>
          <p className="text-[11px] text-[#8a8f98] font-medium mb-2">{results.length} results</p>
          <div className="linear-card overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="text-left text-[10px] text-[#8a8f98] border-b border-white/[0.06]">
                <tr>
                  {Object.keys(results[0]).map((k) => (<th key={k} className="px-3 py-2 font-medium">{k}</th>))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {results.map((row, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    {Object.keys(results[0]).map((k) => (
                      <td key={k} className="px-3 py-2 text-[#d0d6e0] max-w-xs truncate">{String((row as Record<string, unknown>)[k] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && results.length === 0 && !error && <EmptyState text="Configure search parameters and click Run" />}
    </div>
  );
}
