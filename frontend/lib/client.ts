import type {
  AgencySettings,
  Client,
  ConsentRecord,
  Contract,
  Dashboard,
  EnhancedDashboard,
  InboundMessage,
  Interview,
  Job,
  Match,
  Plan,
  Seeker,
  Session,
  Subscription,
  TeamMember,
  TimelinePoint,
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

function toQuery(params?: Record<string, any>): string {
  if (!params) return '';
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '');
  return new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
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
  clients: () => apiFetch<Client[]>("/contracts/clients/list"),
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
    apiFetch<Job>("/scrape/jobs", { method: "POST", body: JSON.stringify(data) }),
  scrapeCandidates: (data: Record<string, unknown>) =>
    apiFetch<Job>("/scrape/candidates", { method: "POST", body: JSON.stringify(data) }),
  // Bulk import
  importCsvPreview: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<{ rows: Record<string, unknown>[]; auto_mapping: Record<string, string>; total: number }>("/tools/import/csv/preview", { method: "POST", body: form });
  },
  importCsv: (file: File, mapping?: Record<string, string>, consentBasis?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (mapping) form.append("mapping", JSON.stringify(mapping));
    const params = new URLSearchParams();
    if (consentBasis) params.set("consent_basis", consentBasis);
    const qs = params.toString();
    return apiFetch<{ imported: number; skipped: number; errors: string[] }>(`/tools/import/csv${qs ? `?${qs}` : ""}`, { method: "POST", body: form });
  },
  // Enrichment
  enrichCandidate: (data: Record<string, unknown>) =>
    apiFetch<{ sources: string[]; data: Record<string, unknown> }>("/tools/enrich", { method: "POST", body: JSON.stringify(data) }),
  // Portal
  portalToken: (seekerId: number) =>
    apiFetch<{ token: string; url: string }>(`/tools/portal/${seekerId}/token`, { method: "GET" }),
  // Artifacts
  misReport: () =>
    apiFetch<{ content: string; filename: string }>("/tools/artifacts/mis"),
  hotlist: () =>
    apiFetch<{ content: string; filename: string }>("/tools/artifacts/hotlist"),
  rtr: (matchId: number) =>
    apiFetch<{ content: string; filename: string }>(`/tools/artifacts/rtr?match_id=${matchId}`),
  offerLetter: (data: Record<string, unknown>) =>
    apiFetch<{ content: string; filename: string }>("/tools/artifacts/offer-letter", { method: "POST", body: JSON.stringify(data) }),
  // Compliance
  i9: (data: Record<string, unknown>) =>
    apiFetch<{ content: string; filename: string }>("/tools/compliance/i9", { method: "POST", body: JSON.stringify(data) }),
  everify: (data: Record<string, unknown>) =>
    apiFetch<{ content: string; filename: string }>("/tools/compliance/everify", { method: "POST", body: JSON.stringify(data) }),
  msa: (data: Record<string, unknown>) =>
    apiFetch<{ content: string; filename: string }>("/tools/compliance/msa", { method: "POST", body: JSON.stringify(data) }),
  // Audit
  // Individual resources
  seeker: (id: number) => apiFetch<Seeker>(`/seekers/${id}`),
  updateSeeker: (id: number, data: Record<string, unknown>) =>
    apiFetch<Seeker>(`/seekers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  contract: (id: number) => apiFetch<Contract>(`/contracts/${id}`),
  updateContract: (id: number, data: Record<string, unknown>) =>
    apiFetch<Contract>(`/contracts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  setContractStatus: (id: number, status: string) =>
    apiFetch<Contract>(`/contracts/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  match: (id: number) => apiFetch<Match>(`/matches/${id}`),
  // Tags
  tags: () => apiFetch<{ id: number; agency_id: number; name: string; color: string }[]>("/tags"),
  createTag: (name: string, color?: string) =>
    apiFetch<{ id: number; agency_id: number; name: string; color: string }>("/tags", {
      method: "POST",
      body: JSON.stringify({ name, color: color ?? "#5e6ad2" }),
    }),
  deleteTag: (tagId: number) =>
    apiFetch<{ ok: boolean }>(`/tags/${tagId}`, { method: "DELETE" }),
  seekerTags: (seekerId: number) =>
    apiFetch<{ id: number; agency_id: number; name: string; color: string }[]>(`/tags/seeker/${seekerId}`),
  attachTag: (seekerId: number, tagId: number) =>
    apiFetch<{ ok: boolean }>(`/tags/seeker/${seekerId}/attach?tag_id=${tagId}`, { method: "POST" }),
  detachTag: (seekerId: number, tagId: number) =>
    apiFetch<{ ok: boolean }>(`/tags/seeker/${seekerId}/detach?tag_id=${tagId}`, { method: "POST" }),
  // Notes
  notes: (entityType: string, entityId: number) =>
    apiFetch<{ id: number; agency_id: number; user_id: number; entity_type: string; entity_id: number; content: string; is_pinned: boolean; created_at: string; updated_at: string }[]>(
      `/notes?entity_type=${entityType}&entity_id=${entityId}`,
    ),
  createNote: (entityType: string, entityId: number, content: string) =>
    apiFetch<{ id: number; agency_id: number; user_id: number; entity_type: string; entity_id: number; content: string; is_pinned: boolean; created_at: string; updated_at: string }>("/notes", {
      method: "POST",
      body: JSON.stringify({ entity_type: entityType, entity_id: entityId, content }),
    }),
  deleteNote: (noteId: number) =>
    apiFetch<{ ok: boolean }>(`/notes/${noteId}`, { method: "DELETE" }),
  // Notifications
  notifications: (unreadOnly = false) =>
    apiFetch<{ id: number; title: string; message: string; notification_type: string; is_read: boolean; read_at: string | null; related_entity_type: string | null; related_entity_id: number | null; action_url: string | null; created_at: string }[]>(
      `/notifications${unreadOnly ? "?unread_only=true" : ""}`,
    ),
  unreadCount: () => apiFetch<{ count: number }>("/notifications/unread-count"),
  markNotificationRead: (id: number) =>
    apiFetch<{ ok: boolean }>(`/notifications/${id}/read`, { method: "PATCH" }),
  markAllNotificationsRead: () =>
    apiFetch<{ ok: boolean }>("/notifications/read-all", { method: "POST" }),
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
  // Settings
  getSettings: () => apiFetch<AgencySettings>("/settings"),
  updateSettings: (data: Record<string, unknown>) =>
    apiFetch<AgencySettings>("/settings", { method: "PATCH", body: JSON.stringify(data) }),
  // Team
  updateTeamMember: (id: number, data: Record<string, unknown>) =>
    apiFetch<TeamMember>(`/auth/users/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  resetPassword: (id: number) =>
    apiFetch<{ temp_password: string }>(`/auth/users/${id}/reset-password`, { method: "POST" }),
  // Interviews
  interviews: (params = "") => apiFetch<Interview[]>(`/interviews${params}`),
  createInterview: (data: Record<string, unknown>) =>
    apiFetch<Interview>("/interviews", { method: "POST", body: JSON.stringify(data) }),
  updateInterview: (id: number, data: Record<string, unknown>) =>
    apiFetch<Interview>(`/interviews/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  cancelInterview: (id: number) =>
    apiFetch<Interview>(`/interviews/${id}/cancel`, { method: "PATCH" }),
  // Clients (CRUD)
  createClient: (data: Record<string, unknown>) =>
    apiFetch<Client>("/contracts/clients", { method: "POST", body: JSON.stringify(data) }),
  updateClient: (id: number, data: Record<string, unknown>) =>
    apiFetch<Client>(`/contracts/clients/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteClient: (id: number) =>
    apiFetch<void>(`/contracts/clients/${id}`, { method: "DELETE" }),
  deleteInterview: (id: number) =>
    apiFetch<void>(`/interviews/${id}`, { method: "DELETE" }),
  updateNote: (id: number, data: Record<string, unknown>) =>
    apiFetch<{ id: number; agency_id: number; user_id: number; entity_type: string; entity_id: number; content: string; is_pinned: boolean; created_at: string; updated_at: string }>(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  team: () => apiFetch<TeamMember[]>("/auth/users"),
  dashboardEnhanced: () => apiFetch<EnhancedDashboard>("/billing/dashboard/enhanced"),
  dashboardTimeline: (days?: number) => apiFetch<TimelinePoint[]>(`/billing/dashboard/timeline${days ? `?days=${days}` : ""}`),
  // Email
  emailSend: (data: {
    to_email: string;
    subject: string;
    body_html: string;
    body_text?: string;
    template_name?: string;
    template_vars?: Record<string, string>;
    related_entity_type?: string;
    related_entity_id?: number;
  }) => apiFetch<any>("/email/send", { method: "POST", body: JSON.stringify(data) }),
  emailHistory: (params?: { status?: string; limit?: number; offset?: number }) =>
    apiFetch<any[]>(`/email/history?${toQuery(params)}`),
  emailTemplates: () => apiFetch<any[]>("/email/templates"),
  emailPreview: (data: {
    subject: string;
    body_html: string;
    template_name?: string;
    template_vars?: Record<string, string>;
  }) => apiFetch<{ html: string }>("/email/preview", { method: "POST", body: JSON.stringify(data) }),
  // Activity
  activityLog: (params?: {
    entity_type?: string;
    entity_id?: number;
    action?: string;
    limit?: number;
    offset?: number;
  }) => apiFetch<any[]>(`/activity?${toQuery(params)}`),
};