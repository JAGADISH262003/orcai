"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, login } from "@/lib/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message as string);
      } else {
        setError("Login failed");
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
          <h1 className="text-xl font-semibold tracking-tight">Sign in to ORCAI</h1>
          <p className="text-xs text-[#8a8f98]">Agency command center</p>
        </div>

        <form onSubmit={submit} className="linear-card p-6 space-y-4 bg-[#0f1011] border-white/10">
          {error ? (
            <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-300">
              {error}
            </div>
          ) : null}
          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8a8f98] font-medium">Email</label>
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="linear-input w-full px-3 py-2 text-sm"
              placeholder="••••••••"
            />
          </div>
          <button
            disabled={busy}
            className="w-full py-2.5 rounded-md bg-brand hover:bg-brand-hover text-white text-sm font-medium transition disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-xs text-[#8a8f98]">
          New agency?{" "}
          <Link href="/register" className="text-brand-light hover:underline">
            Create an account
          </Link>
        </p>
        <p className="text-center text-[10px] text-[#62666d] font-mono">
          demo: owner@taproot.io / Orcai@12345
        </p>
      </div>
    </div>
  );
}