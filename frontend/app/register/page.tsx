"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, api, register } from "@/lib/client";
import type { WorkflowBlueprint } from "@/lib/types";

export default function RegisterPage() {
  const router = useRouter();
  const [agencyName, setAgencyName] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [workflows, setWorkflows] = useState<WorkflowBlueprint[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState("");

  useEffect(() => {
    api.workflows().then((cat) => {
      setWorkflows(cat.workflows);
      setSelectedWorkflow(cat.default);
    }).catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(agencyName, name, email, password, selectedWorkflow || undefined);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message as string);
      } else {
        setError("Registration failed");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 mx-auto rounded bg-gradient-to-br from-brand to-indigo-600 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-brand/20">
            O
          </div>
          <h1 className="text-xl font-semibold tracking-tight">Launch your agency</h1>
          <p className="text-xs text-[#8a8f98]">Multi-tenant recruiting OS · 14-day trial</p>
        </div>

        <form onSubmit={submit} className="linear-card p-6 space-y-4 bg-[#0f1011] border-white/10">
          {error ? (
            <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">
              {error}
            </div>
          ) : null}
          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8a8f98] font-medium">Agency / Company name</label>
            <input
              required
              value={agencyName}
              onChange={(e) => setAgencyName(e.target.value)}
              className="linear-input w-full px-3 py-2 text-sm"
              placeholder="TapRoot Consulting"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8a8f98] font-medium">Your name</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="linear-input w-full px-3 py-2 text-sm"
              placeholder="Jane Doe"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8a8f98] font-medium">Work email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="linear-input w-full px-3 py-2 text-sm"
              placeholder="you@agency.com"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8a8f98] font-medium">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="linear-input w-full px-3 py-2 text-sm"
              placeholder="Min 8 characters"
            />
          </div>
          {workflows.length > 0 ? (
            <div className="space-y-1.5">
              <label className="text-[11px] text-[#8a8f98] font-medium">Company type</label>
              <select
                value={selectedWorkflow}
                onChange={(e) => setSelectedWorkflow(e.target.value)}
                className="linear-input w-full px-3 py-2 text-sm"
              >
                {workflows.map((wf) => (
                  <option key={wf.key} value={wf.key}>
                    {wf.icon ? `${wf.icon} ` : ""}{wf.label}
                  </option>
                ))}
              </select>
              {workflows.find((w) => w.key === selectedWorkflow)?.description ? (
                <p className="text-[10px] text-[#62666d]">
                  {workflows.find((w) => w.key === selectedWorkflow)!.description}
                </p>
              ) : null}
            </div>
          ) : null}
          <button
            disabled={busy}
            className="w-full py-2.5 rounded-md bg-brand hover:bg-brand-hover text-white text-sm font-medium transition disabled:opacity-50"
          >
            {busy ? "Creating agency…" : "Create agency"}
          </button>
        </form>

        <p className="text-center text-xs text-[#8a8f98]">
          Already registered?{" "}
          <Link href="/login" className="text-brand-light hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}