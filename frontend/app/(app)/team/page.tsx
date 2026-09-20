"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/UI";
import { api } from "@/lib/client";

interface UserRow {
  id: number;
  name: string;
  email: string;
  role: string;
}

const ROLES = ["owner", "admin", "recruiter", "client"] as const;

function roleTone(role: string): string {
  switch (role) {
    case "owner": return "brand";
    case "admin": return "purple";
    case "recruiter": return "blue";
    case "client": return "slate";
    default: return "slate";
  }
}

export default function TeamPage() {
  const [members, setMembers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const users = await api.users();
      setMembers(users);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load team");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function updateRole(id: number, role: string) {
    try {
      await api.updateTeamMember(id, { role });
      setMembers((prev) => prev.map((m) => (m.id === id ? { ...m, role } : m)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update role");
    }
  }

  async function handleResetPassword(id: number, name: string) {
    if (!confirm(`Reset password for ${name}?`)) return;
    try {
      const res = await api.resetPassword(id);
      setToast(`Temporary password for ${name}: ${res.temp_password}`);
      setTimeout(() => setToast(null), 8000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reset password");
    }
  }

  if (loading) return <Loading label="Loading team…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[#f7f8f8]">Team Management</h1>
        <p className="text-xs text-[#8a8f98] mt-1">Manage agency users, roles, and access permissions.</p>
      </div>

      {toast && (
        <div className="p-3 rounded bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 font-mono">{toast}</div>
      )}

      {members.length === 0 ? (
        <EmptyState text="No team members found." />
      ) : (
        <div className="linear-card overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-[#8a8f98] font-mono text-[11px]">
                <th className="py-2.5 px-3">Member</th>
                <th className="py-2.5 px-3">Email</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-[#d0d6e0]">
              {members.map((m) => (
                <tr key={m.id} className="hover:bg-white/[0.02]">
                  <td className="py-3 px-3">
                    <div className="font-medium text-[#f7f8f8]">{m.name}</div>
                  </td>
                  <td className="py-3 px-3 text-[#8a8f98]">{m.email}</td>
                  <td className="py-3 px-3">
                    <select
                      value={m.role}
                      onChange={(e) => updateRole(m.id, e.target.value)}
                      className="linear-input px-2 py-1 text-[10px] rounded"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-3 px-3">
                    <button
                      onClick={() => handleResetPassword(m.id, m.name)}
                      className="px-2 py-1 rounded bg-white/[0.06] hover:bg-white/[0.1] text-[10px] text-[#d0d6e0]"
                    >
                      Reset password
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
