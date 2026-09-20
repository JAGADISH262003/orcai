"use client";

import { useState } from "react";
import { EmptyState, ErrorBanner } from "@/components/UI";
import { api } from "@/lib/client";

export default function ToolsPage() {
  const [tab, setTab] = useState<"enrich" | "artifacts" | "compliance">("enrich");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const [enrichEmail, setEnrichEmail] = useState("");
  const [enrichName, setEnrichName] = useState("");
  const [enrichDomain, setEnrichDomain] = useState("");

  const [candidateName, setCandidateName] = useState("");
  const [positionTitle, setPositionTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [salary, setSalary] = useState("");
  const [location, setLocation] = useState("");

  const [employeeName, setEmployeeName] = useState("");
  const [address, setAddress] = useState("");
  const [dob, setDob] = useState("");
  const [ssnLast4, setSsnLast4] = useState("");
  const [phone, setPhone] = useState("");
  const [citizenship, setCitizenship] = useState("");

  const [employerName, setEmployerName] = useState("");
  const [ein, setEin] = useState("");
  const [i9Date, setI9Date] = useState("");

  const [vendorName, setVendorName] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");

  async function handleEnrich() {
    setLoading(true); setError(null);
    try {
      const data = await api.enrichCandidate({ email: enrichEmail || undefined, name: enrichName || undefined, domain: enrichDomain || undefined });
      setResult(JSON.stringify(data, null, 2));
    } catch (e) { setError(e instanceof Error ? e.message : "Enrichment failed"); }
    finally { setLoading(false); }
  }

  async function handleArtifact(type: string) {
    setLoading(true); setError(null);
    try {
      let data: { content: string; filename: string } | undefined;
      if (type === "mis") data = await api.misReport();
      else if (type === "hotlist") data = await api.hotlist();
      else if (type === "offer-letter") data = await api.artifactOfferLetter({ candidate_name: candidateName, position_title: positionTitle, company_name: companyName, start_date: startDate, salary, location });
      if (data && "content" in data) setResult(data.content);
    } catch (e) { setError(e instanceof Error ? e.message : "Generation failed"); }
    finally { setLoading(false); }
  }

  async function handleCompliance(type: string) {
    setLoading(true); setError(null);
    try {
      let data;
      if (type === "i9") data = await api.i9({ employee_name: employeeName, address, date_of_birth: dob, ssn_last4: ssnLast4, phone, citizenship_status: citizenship });
      else if (type === "e-verify") data = await api.everify({ employee_name: employeeName, employer_name: employerName, employer_ein: ein, i9_date: i9Date });
      else if (type === "msa") data = await api.msa({ client_name: companyName, vendor_name: vendorName, effective_date: effectiveDate });
      if (data) setResult(data.content);
    } catch (e) { setError(e instanceof Error ? e.message : "Compliance generation failed"); }
    finally { setLoading(false); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Tools & Compliance</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Enrichment, output artifacts, and US compliance document generation.</p>
      </div>

      <div className="flex gap-2 border-b border-white/[0.06] pb-2">
        {(["enrich", "artifacts", "compliance"] as const).map((t) => (
          <button key={t}
            className={`px-3 py-1 text-xs font-medium rounded transition ${tab === t ? "bg-[#5e6ad2] text-white" : "text-[#8a8f98] hover:text-[#d0d6e0] hover:bg-white/[0.04]"}`}
            onClick={() => { setTab(t); setResult(null); setError(null); }}>
            {t === "enrich" ? "Enrichment" : t === "artifacts" ? "Output Artifacts" : "US Compliance"}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message={error} />}

      {tab === "enrich" && (
        <div className="space-y-4">
          <p className="text-xs text-[#8a8f98]">Enrich candidate data using Apollo.io, PDL, and Hunter.io APIs.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Email</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={enrichEmail} onChange={(e) => setEnrichEmail(e.target.value)} placeholder="candidate@example.com" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Full Name</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={enrichName} onChange={(e) => setEnrichName(e.target.value)} placeholder="John Smith" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Domain</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={enrichDomain} onChange={(e) => setEnrichDomain(e.target.value)} placeholder="example.com" /></div>
          </div>
          <button className="bg-brand hover:bg-brand-hover text-white text-xs font-medium px-3.5 py-1.5 rounded-md transition shadow disabled:opacity-50"
            onClick={handleEnrich} disabled={loading || (!enrichEmail && !enrichName && !enrichDomain)}>
            {loading ? "Enriching..." : "Enrich"}
          </button>
        </div>
      )}

      {tab === "artifacts" && (
        <div className="space-y-4">
          <p className="text-xs text-[#8a8f98]">Generate MIS reports, hotlists, RTR documents, and offer letters.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Candidate Name</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={candidateName} onChange={(e) => setCandidateName(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Position Title</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={positionTitle} onChange={(e) => setPositionTitle(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Company Name</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={companyName} onChange={(e) => setCompanyName(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Start Date</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={startDate} onChange={(e) => setStartDate(e.target.value)} placeholder="2026-01-01" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Salary</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={salary} onChange={(e) => setSalary(e.target.value)} placeholder="$120,000" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Location</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="San Francisco, CA" /></div>
          </div>
          <div className="flex gap-3 flex-wrap">
            <button className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50" onClick={() => handleArtifact("mis")} disabled={loading}>MIS Report</button>
            <button className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50" onClick={() => handleArtifact("hotlist")} disabled={loading}>Hotlist</button>
            <button className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50" onClick={() => handleArtifact("offer-letter")} disabled={loading || !candidateName}>Offer Letter</button>
          </div>
        </div>
      )}

      {tab === "compliance" && (
        <div className="space-y-4">
          <p className="text-xs text-[#8a8f98]">Generate US compliance documents: I-9, E-Verify, and MSA templates.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Employee Name</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Address</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={address} onChange={(e) => setAddress(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Date of Birth</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={dob} onChange={(e) => setDob(e.target.value)} placeholder="1990-01-01" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">SSN Last 4</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={ssnLast4} onChange={(e) => setSsnLast4(e.target.value)} placeholder="1234" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Phone</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={phone} onChange={(e) => setPhone(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Citizenship Status</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={citizenship} onChange={(e) => setCitizenship(e.target.value)} placeholder="US Citizen" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Employer Name</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={employerName} onChange={(e) => setEmployerName(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">EIN</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={ein} onChange={(e) => setEin(e.target.value)} placeholder="12-3456789" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">I-9 Date</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={i9Date} onChange={(e) => setI9Date(e.target.value)} placeholder="2026-01-01" /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Vendor Name (MSA)</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={vendorName} onChange={(e) => setVendorName(e.target.value)} /></div>
            <div><label className="block text-[11px] text-[#8a8f98] mb-1">Effective Date (MSA)</label><input className="linear-input w-full px-3 py-1.5 text-xs" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} placeholder="2026-01-01" /></div>
          </div>
          <div className="flex gap-3 flex-wrap">
            <button className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50" onClick={() => handleCompliance("i9")} disabled={loading || !employeeName}>I-9 Form</button>
            <button className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50" onClick={() => handleCompliance("e-verify")} disabled={loading || !employeeName}>E-Verify Case</button>
            <button className="linear-card px-3.5 py-1.5 text-xs font-medium text-[#d0d6e0] hover:text-white transition disabled:opacity-50" onClick={() => handleCompliance("msa")} disabled={loading || !vendorName}>MSA Template</button>
          </div>
        </div>
      )}

      {result && (
        <div className="mt-4">
          <p className="text-[11px] text-[#8a8f98] font-medium mb-1">Output</p>
          <pre className="linear-card p-4 text-xs overflow-auto max-h-96 whitespace-pre-wrap text-[#d0d6e0]">{result}</pre>
        </div>
      )}

      {!result && !loading && !error && <EmptyState text="Select a tool and configure parameters" />}
    </div>
  );
}
