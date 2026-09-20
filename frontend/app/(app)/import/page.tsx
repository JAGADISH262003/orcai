"use client";

import { useState } from "react";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
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
      <h1 className="text-xl font-bold">Bulk Candidate Import</h1>
      <p className="text-sm text-gray-500">Upload a CSV (or ZIP of CSVs) to import candidates in bulk. Column auto-detection maps common header names to candidate fields.</p>

      <div className="border-2 border-dashed rounded-lg p-6 text-center">
        <input
          type="file"
          accept=".csv,.zip"
          className="hidden"
          id="file-input"
          onChange={(e) => { setFile(e.target.files?.[0] ?? null); setPreview(null); setResult(null); }}
        />
        <label htmlFor="file-input" className="cursor-pointer text-sm text-gray-600">
          {file ? (
            <span className="font-medium text-blue-600">{file.name}</span>
          ) : (
            "Click to select CSV or ZIP file"
          )}
        </label>
      </div>

      {file && !preview && (
        <button
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:opacity-50"
          onClick={handlePreview}
          disabled={loading}
        >
          {loading ? "Analyzing..." : "Preview & Map Columns"}
        </button>
      )}

      {error && <ErrorBanner message={error} />}

      {preview && (
        <div className="space-y-4">
          <div className="bg-gray-50 rounded p-3 text-sm">
            <strong>{preview.total}</strong> rows detected. Review and adjust column mappings below.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(mapping).map(([csvCol, candidateField]) => (
              <div key={csvCol} className="flex items-center gap-2 text-sm">
                <span className="font-mono bg-gray-100 px-2 py-1 rounded min-w-[120px]">{csvCol}</span>
                <span className="text-gray-400">→</span>
                <select
                  className="border rounded px-2 py-1 flex-1"
                  value={candidateField}
                  onChange={(e) => setMapping((m) => ({ ...m, [csvCol]: e.target.value }))}
                >
                  <option value="">(skip)</option>
                  {["name", "email", "phone", "location", "current_title", "current_company",
                    "skills", "education", "experience_years", "visa_status", "linkedin_url",
                    "github_url", "portfolio_url", "notes"].map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Consent Basis</label>
            <select
              className="border rounded px-2 py-1.5 text-sm"
              value={consentBasis}
              onChange={(e) => setConsentBasis(e.target.value)}
            >
              <option value="affidavit">Affidavit (self-declared)</option>
              <option value="direct_consent">Direct Consent</option>
              <option value="legitimate_interest">Legitimate Interest</option>
              <option value="public_data">Public Data</option>
            </select>
          </div>

          <div className="flex gap-3">
            <button
              className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 disabled:opacity-50"
              onClick={handleImport}
              disabled={loading}
            >
              {loading ? "Importing..." : `Import ${preview.total} Candidates`}
            </button>
            <button
              className="px-4 py-2 border text-sm rounded hover:bg-gray-50"
              onClick={() => { setPreview(null); setResult(null); }}
            >
              Cancel
            </button>
          </div>

          {preview.rows.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 mb-1">First 5 rows preview</h3>
              <div className="overflow-x-auto border rounded text-xs">
                <table className="min-w-full">
                  <thead className="bg-gray-50 text-left">
                    <tr>
                      {Object.keys(preview.rows[0]).map((k) => (
                        <th key={k} className="px-2 py-1 font-medium">{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {preview.rows.slice(0, 5).map((row, i) => (
                      <tr key={i}>
                        {Object.keys(preview.rows[0]).map((k) => (
                          <td key={k} className="px-2 py-1">{String((row as Record<string, unknown>)[k] ?? "")}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded p-4 space-y-2">
          <p className="text-sm font-semibold text-green-800">Import Complete</p>
          <p className="text-sm text-green-700">Imported: {result.imported} | Skipped: {result.skipped}</p>
          {result.errors.length > 0 && (
            <div className="text-sm text-red-600">
              <p className="font-medium">Errors:</p>
              <ul className="list-disc pl-4">
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {!file && !preview && !result && (
        <EmptyState text="Select a CSV or ZIP file to begin" />
      )}
    </div>
  );
}
