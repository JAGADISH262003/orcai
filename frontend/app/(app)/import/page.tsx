"use client";

import { useState } from "react";
import { EmptyState, ErrorBanner } from "@/components/UI";
import { api } from "@/lib/client";

interface PreviewData {
  rows: Record<string, unknown>[];
  auto_mapping: Record<string, string>;
  total: number;
}

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [consentBasis, setConsentBasis] = useState("affidavit");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ imported: number; skipped: number; errors: string[] } | null>(null);

  async function handlePreview() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.importCsvPreview(file);
      setPreview(data);
      setMapping(data.auto_mapping);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleImport() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.importCsv(file, mapping, consentBasis);
      setResult(data);
      setPreview(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Bulk Candidate Import</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Upload a CSV (or ZIP of CSVs) to import candidates in bulk with auto-detected column mapping.</p>
      </div>

      <div className="linear-card border-2 border-dashed p-8 text-center">
        <input type="file" accept=".csv,.zip" className="hidden" id="file-input"
          onChange={(e) => { setFile(e.target.files?.[0] ?? null); setPreview(null); setResult(null); }} />
        <label htmlFor="file-input" className="cursor-pointer text-xs text-[#8a8f98] hover:text-[#d0d6e0] transition">
          {file ? <span className="font-medium text-[#5e6ad2]">{file.name}</span> : "Click to select CSV or ZIP file"}
        </label>
      </div>

      {file && !preview && (
        <button className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow disabled:opacity-50"
          onClick={handlePreview} disabled={loading}>
          {loading ? "Analyzing..." : "Preview & Map Columns"}
        </button>
      )}

      {error && <ErrorBanner message={error} />}

      {preview && (
        <div className="space-y-4">
          <div className="linear-card p-3 text-xs text-[#d0d6e0]">
            <strong className="text-[#f7f8f8]">{preview.total}</strong> rows detected. Review and adjust column mappings below.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(mapping).map(([csvCol, candidateField]) => (
              <div key={csvCol} className="flex items-center gap-2 text-xs">
                <span className="font-mono bg-white/[0.04] px-2 py-1 rounded min-w-[120px] text-[#d0d6e0]">{csvCol}</span>
                <span className="text-[#8a8f98]">&rarr;</span>
                <select className="linear-input flex-1 px-2 py-1 text-xs" value={candidateField} onChange={(e) => setMapping((m) => ({ ...m, [csvCol]: e.target.value }))}>
                  <option value="">(skip)</option>
                  {["name", "email", "phone", "location", "current_title", "current_company", "skills", "education", "experience_years", "visa_status", "linkedin_url", "github_url", "portfolio_url", "notes"].map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          <div>
            <label className="block text-[11px] font-medium text-[#8a8f98] mb-1">Consent Basis</label>
            <select className="linear-input px-3 py-1.5 text-xs" value={consentBasis} onChange={(e) => setConsentBasis(e.target.value)}>
              <option value="affidavit">Affidavit (self-declared)</option>
              <option value="direct_consent">Direct Consent</option>
              <option value="legitimate_interest">Legitimate Interest</option>
              <option value="public_data">Public Data</option>
            </select>
          </div>

          <div className="flex gap-3">
            <button className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow disabled:opacity-50"
              onClick={handleImport} disabled={loading}>
              {loading ? "Importing..." : `Import ${preview.total} Candidates`}
            </button>
            <button className="linear-card px-3.5 py-1.5 text-xs text-[#d0d6e0] hover:text-white transition"
              onClick={() => { setPreview(null); setResult(null); }}>Cancel</button>
          </div>

          {preview.rows.length > 0 && (
            <div>
              <p className="text-[11px] text-[#8a8f98] font-medium mb-1">First 5 rows preview</p>
              <div className="linear-card overflow-x-auto text-xs">
                <table className="min-w-full">
                  <thead className="text-left text-[10px] text-[#8a8f98] border-b border-white/[0.06]">
                    <tr>{Object.keys(preview.rows[0]).map((k) => (<th key={k} className="px-2 py-1 font-medium">{k}</th>))}</tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {preview.rows.slice(0, 5).map((row, i) => (
                      <tr key={i}>{Object.keys(preview.rows[0]).map((k) => (
                        <td key={k} className="px-2 py-1 text-[#d0d6e0]">{String((row as Record<string, unknown>)[k] ?? "")}</td>
                      ))}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="linear-card p-4 space-y-2 border-green-500/20">
          <p className="text-xs font-semibold text-green-400">Import Complete</p>
          <p className="text-xs text-[#d0d6e0]">Imported: {result.imported} | Skipped: {result.skipped}</p>
          {result.errors.length > 0 && (
            <div className="text-xs text-red-400">
              <p className="font-medium">Errors:</p>
              <ul className="list-disc pl-4">{result.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      {!file && !preview && !result && <EmptyState text="Select a CSV or ZIP file to begin" />}
    </div>
  );
}
