import type {
  Client,
  ConsentRecord,
  Contract,
  Dashboard,
  InboundMessage,
  Job,
  Match,
  Plan,
  Seeker,
  Session,
  Subscription,
  WorkflowCatalog,
} from "@/lib/types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function rawFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  _retried = false,
): Promise<T> {
  try {
    return await rawFetch<T>(path, options);
  } catch (err) {
    if (err instanceof ApiError && err.status === 401 && !_retried) {
      if (path === "/auth/login" || path === "/auth/register") throw err;
      const renewed = await rawFetch<Session>("/auth/refresh", { method: "POST" });
      if (!renewed || !renewed.user) throw err;
      return apiFetch<T>(path, options, true);
    }
    throw err;
  }
}

// Polls a background job until it reaches a terminal state.
export async function pollJob(
  id: number,
  { interval = 1200, timeout = 180000 } = {},
): Promise<Job> {
  const deadline = Date.now() + timeout;
  for (;;) {
    const job = await apiFetch<Job>(`/jobs/${id}`);
    if (job.status === "done" || job.status === "failed") {
      if (job.status === "failed") {
        throw new ApiError(500, job.error ?? "Background job failed");
      }
      return job;
    }
    if (Date.now() > deadline) {
      throw new ApiError(500, "Timed out waiting for background job");
    }
    await new Promise((r) => setTimeout(r, interval));
  }
}

// Auth helpers call the dedicated BFF route handlers.
export async function login(email: string, password: string): Promise<Session> {
  return apiFetch<Session>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(
  agencyName: string,
  name: string,
  email: string,
  password: string,
  workflowType?: string,
): Promise<Session> {
  const body: Record<string, string> = {
    agency_name: agencyName,
    name,
    email,
    password,
  };
  if (workflowType) body.workflow_type = workflowType;
  return apiFetch<Session>("/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchMe(): Promise<Session | null> {
  try {
    return await apiFetch<Session>("/auth/me");
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    /* ignore */
  }
}

// Resource helpers (proxied to the backend by middleware)
export const api = {
  dashboard: () => apiFetch<Dashboard>("/billing/dashboard"),
  job: (id: number) => apiFetch<Job>(`/jobs/${id}`),
  contracts: () => apiFetch<Contract[]>("/contracts"),
  createContract: (raw_text: string, client_name?: string) =>
    apiFetch<Job>("/contracts?async=true", {
      method: "POST",
      body: JSON.stringify({ raw_text, client_name }),
    }),
  clients: () => apiFetch<Client[]>("/clients/list"),
  seekers: (params = "") => apiFetch<Seeker[]>(`/seekers${params}`),
  createSeeker: (data: Record<string, unknown>) =>
    apiFetch<Seeker>("/seekers", { method: "POST", body: JSON.stringify(data) }),
  uploadResume: (file: File, visa_status?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (visa_status) form.append("visa_status", visa_status);
    return apiFetch<Job>("/seekers/upload", { method: "POST", body: form });
  },
  matches: (params = "") => apiFetch<Match[]>(`/matches${params}`),
  runMatching: (contractId?: number) =>
    apiFetch<Job>(`/matches/run${contractId ? `?contract_id=${contractId}` : ""}`, {
      method: "POST",
    }),
  setMatchStatus: (matchId: number, status: string) =>
    apiFetch<Match>(`/matches/${matchId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  hitlQueue: () => apiFetch<Match[]>("/hitl"),
  reviewHitl: (matchId: number, decision: string, review?: string) =>
    apiFetch<Match>(`/hitl/${matchId}/review`, {
      method: "PATCH",
      body: JSON.stringify({ decision, review }),
    }),
  inbound: () => apiFetch<InboundMessage[]>("/inbound"),
  ingestInbound: (data: Record<string, unknown>) =>
    apiFetch<Job>("/inbound/message", { method: "POST", body: JSON.stringify(data) }),
  consent: () => apiFetch<ConsentRecord[]>("/consent"),
  eraseConsent: (id: number) =>
    apiFetch<ConsentRecord>(`/consent/${id}/erase`, { method: "POST" }),
  withdrawConsent: (id: number) =>
    apiFetch<ConsentRecord>(`/consent/${id}/withdraw`, { method: "PATCH" }),
  plans: () => apiFetch<Plan[]>("/billing/plans"),
  subscription: () => apiFetch<Subscription>("/billing/subscription"),
  selectPlan: (slug: string) =>
    apiFetch<Subscription>(`/billing/subscription/select/${slug}`, { method: "POST" }),
  users: () => apiFetch<{ id: number; name: string; email: string; role: string }[]>("/auth/users"),
  workflows: () => apiFetch<WorkflowCatalog>("/workflows"),
  // Scrapers
  scrapeJobs: (data: Record<string, unknown>) =>
    apiFetch<Job>("/scrapers/jobs", { method: "POST", body: JSON.stringify(data) }),
  scrapeCandidates: (data: Record<string, unknown>) =>
    apiFetch<Job>("/scrapers/candidates", { method: "POST", body: JSON.stringify(data) }),
  // Bulk import
  importCsvPreview: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<{ rows: Record<string, unknown>[]; auto_mapping: Record<string, string>; total: number }>("/tools/import/csv/preview", { method: "POST", body: form });
  },
  importCsv: (file: File, mapping?: Record<string, string>) => {
    const form = new FormData();
    form.append("file", file);
    if (mapping) form.append("mapping", JSON.stringify(mapping));
    return apiFetch<{ imported: number; skipped: number; errors: string[] }>("/tools/import/csv", { method: "POST", body: form });
  },
  // Enrichment
  enrichCandidate: (data: Record<string, unknown>) =>
    apiFetch<{ sources: string[]; data: Record<string, unknown> }>("/tools/enrich", { method: "POST", body: JSON.stringify(data) }),
  // Portal
  portalToken: (seekerId: number) =>
    apiFetch<{ token: string; url: string }>(`/tools/portal/${seekerId}/token`, { method: "POST" }),
  // Artifacts
  misReport: () =>
    apiFetch<{ content: string; filename: string }>("/tools/artifacts/mis"),
  hotlist: () =>
    apiFetch<{ content: string; filename: string }>("/tools/artifacts/hotlist"),
  rtr: (matchId: number) =>
    apiFetch<{ content: string; filename: string }>(`/tools/artifacts/rtr?match_id=${matchId}`),
  offerLetter: (matchId: number) =>
    apiFetch<{ content: string; filename: string }>(`/tools/artifacts/offer-letter?match_id=${matchId}`),
  // Compliance
  i9: (matchId: number) =>
    apiFetch<{ content: string; filename: string }>(`/tools/compliance/i-9?match_id=${matchId}`),
  everify: (matchId: number) =>
    apiFetch<{ content: string; filename: string }>(`/tools/compliance/e-verify?match_id=${matchId}`),
  msa: (clientId: number) =>
    apiFetch<{ content: string; filename: string }>(`/tools/compliance/msa?client_id=${clientId}`),
  // Audit
  auditLogs: (params = "") =>
    apiFetch<{ id: number; action: string; user_id: number; entity_type: string; entity_id: number; meta: unknown; ip: string; created_at: string }[]>(`/audit${params}`),
  auditStats: () =>
    apiFetch<{ total_events: number; events_this_week: number; by_action: Record<string, number> }>("/audit/stats"),
  // Messaging
  sendWhatsApp: (to_phone: string, text: string) =>
    apiFetch<{ ok: boolean }>("/messaging/whatsapp", { method: "POST", body: JSON.stringify({ to_phone, text }) }),
  sendTelegram: (chat_id: string, text: string) =>
    apiFetch<{ ok: boolean }>("/messaging/telegram", { method: "POST", body: JSON.stringify({ chat_id, text }) }),
};