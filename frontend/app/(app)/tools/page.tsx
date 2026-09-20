"use client";

import { useState } from "react";
import { EmptyState, ErrorBanner } from "@/components/UI";
import { api } from "@/lib/client";

export default function ToolsPage() {
  const [tab, setTab] = useState<"enrich" | "artifacts" | "compliance">("enrich");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  // Enrichment state
  const [enrichEmail, setEnrichEmail] = useState("");
  const [enrichName, setEnrichName] = useState("");
  const [enrichDomain, setEnrichDomain] = useState("");

  // Artifact state
  const [artifactMatchId, setArtifactMatchId] = useState("");
  const [artifactClientId, setArtifactClientId] = useState("");

  async function handleEnrich() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.enrichCandidate({ email: enrichEmail || undefined, name: enrichName || undefined, domain: enrichDomain || undefined });
      setResult(JSON.stringify(data, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Enrichment failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleArtifact(type: string) {
    setLoading(true);
    setError(null);
    try {
      let data;
      if (type === "mis") data = await api.misReport();
      else if (type === "hotlist") data = await api.hotlist();
      else if (type === "rtr") data = await api.rtr(Number(artifactMatchId));
      else if (type === "offer-letter") data = await api.offerLetter({ candidate_name: "", position_title: "", company_name: "", start_date: "", salary: "", location: "" });
      if (data) setResult(data.content);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCompliance(type: string) {
    setLoading(true);
    setError(null);
    try {
      let data;
      if (type === "i-9") data = await api.i9({ employee_name: "", address: "", date_of_birth: "", ssn_last4: "", phone: "", citizenship_status: "" });
      else if (type === "e-verify") data = await api.everify({ employee_name: "", employer_name: "", employer_ein: "", i9_date: "" });
      else if (type === "msa") data = await api.msa({ client_name: "", vendor_name: "", effective_date: "" });
      if (data) setResult(data.content);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compliance generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Tools & Compliance</h1>

      <div className="flex gap-2 border-b pb-2">
        {(["enrich", "artifacts", "compliance"] as const).map((t) => (
          <button
            key={t}
            className={`px-3 py-1 text-sm font-medium rounded-t ${tab === t ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}
            onClick={() => { setTab(t); setResult(null); setError(null); }}
          >
            {t === "enrich" ? "Enrichment" : t === "artifacts" ? "Output Artifacts" : "US Compliance"}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message={error} />}

      {tab === "enrich" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">Enrich candidate data using Apollo.io, PDL, and Hunter.io APIs.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Email</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm" value={enrichEmail} onChange={(e) => setEnrichEmail(e.target.value)} placeholder="candidate@example.com" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Full Name</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm" value={enrichName} onChange={(e) => setEnrichName(e.target.value)} placeholder="John Smith" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Domain</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm" value={enrichDomain} onChange={(e) => setEnrichDomain(e.target.value)} placeholder="example.com" />
            </div>
          </div>
          <button
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:opacity-50"
            onClick={handleEnrich}
            disabled={loading || (!enrichEmail && !enrichName && !enrichDomain)}
          >
            {loading ? "Enriching..." : "Enrich"}
          </button>
        </div>
      )}

      {tab === "artifacts" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">Generate MIS reports, hotlists, RTR documents, and offer letters.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Match ID (for RTR / Offer Letter)</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm" value={artifactMatchId} onChange={(e) => setArtifactMatchId(e.target.value)} placeholder="123" />
            </div>
          </div>
          <div className="flex gap-3 flex-wrap">
            <button className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50" onClick={() => handleArtifact("mis")} disabled={loading}>MIS Report</button>
            <button className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50" onClick={() => handleArtifact("hotlist")} disabled={loading}>Hotlist</button>
            <button className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50" onClick={() => handleArtifact("rtr")} disabled={loading || !artifactMatchId}>RTR Document</button>
            <button className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50" onClick={() => handleArtifact("offer-letter")} disabled={loading || !artifactMatchId}>Offer Letter</button>
          </div>
        </div>
      )}

      {tab === "compliance" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">Generate US compliance documents: I-9, E-Verify, and MSA templates.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Match ID (for I-9 / E-Verify)</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm" value={artifactMatchId} onChange={(e) => setArtifactMatchId(e.target.value)} placeholder="123" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Client ID (for MSA)</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm" value={artifactClientId} onChange={(e) => setArtifactClientId(e.target.value)} placeholder="456" />
            </div>
          </div>
          <div className="flex gap-3 flex-wrap">
            <button className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50" onClick={() => handleCompliance("i-9")} disabled={loading || !artifactMatchId}>I-9 Form</button>
            <button className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50" onClick={() => handleCompliance("e-verify")} disabled={loading || !artifactMatchId}>E-Verify Case</button>
            <button className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50" onClick={() => handleCompliance("msa")} disabled={loading || !artifactClientId}>MSA Template</button>
          </div>
        </div>
      )}

      {result && (
        <div className="mt-4">
          <h3 className="text-xs font-semibold text-gray-500 mb-1">Output</h3>
          <pre className="bg-gray-50 border rounded p-4 text-xs overflow-auto max-h-96 whitespace-pre-wrap">{result}</pre>
        </div>
      )}

      {!result && !loading && !error && (
        <EmptyState text="Select a tool and configure parameters" />
      )}
    </div>
  );
}
