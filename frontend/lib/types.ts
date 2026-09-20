export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  permissions: string[];
  phone?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface WorkflowStage {
  key: string;
  label: string;
}

export interface WorkflowBlueprint {
  key: string;
  label: string;
  description?: string;
  icon?: string;
  stages: WorkflowStage[];
  entry_stage: string;
  fill_stage: string;
  reject_stage: string;
  candidate_fields?: string[];
  job_fields?: string[];
}

export interface WorkflowCatalog {
  default: string;
  workflows: WorkflowBlueprint[];
}

export interface Agency {
  id: number;
  name: string;
  slug: string;
  tier: string;
  workflow_type: string;
  workflow: WorkflowBlueprint;
  description?: string | null;
  created_at: string;
}

export interface Session {
  access_token?: string;
  refresh_token?: string | null;
  user: User;
  agency: Agency;
}

export interface Job {
  id: number;
  agency_id: number;
  type: string;
  status: string;
  attempts: number;
  error?: string | null;
  result?: Record<string, unknown> | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface Contract {
  id: number;
  agency_id: number;
  client_id?: number | null;
  title?: string | null;
  status: string;
  location?: string | null;
  is_remote?: boolean | null;
  duration_months?: number | null;
  rate_bill?: number | null;
  rate_pay?: number | null;
  currency: string;
  experience_min?: number | null;
  openings: number;
  start_by?: string | null;
  skills: string[];
  ai_summary?: string | null;
  parse_method?: string | null;
  created_at: string;
  client_name?: string | null;
}

export interface Client {
  id: number;
  agency_id: number;
  name: string;
  industry?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface Seeker {
  id: number;
  agency_id: number;
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  visa_status?: string | null;
  location?: string | null;
  headline?: string | null;
  skills: string[];
  experience_years?: number | null;
  summary?: string | null;
  education?: string | null;
  source: string;
  source_channel?: string | null;
  resume_path?: string | null;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Match {
  id: number;
  contract_id: number;
  seeker_id: number;
  score: number;
  tier: string;
  status: string;
  hitl_required: boolean;
  rationale?: string | null;
  hitl_status?: string | null;
  human_review?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  seeker_name?: string | null;
  seeker_headline?: string | null;
  seeker_skills: string[];
  contract_title?: string | null;
}

export interface InboundMessage {
  id: number;
  channel: string;
  sender_name?: string | null;
  phone_number?: string | null;
  body: string;
  status: string;
  seeker_id?: number | null;
  received_at: string;
}

export interface ConsentRecord {
  id: number;
  seeker_id: number;
  seeker_name?: string | null;
  basis: string;
  channel?: string | null;
  status: string;
  consent_given_at: string;
  retention_days: number;
  erased_at?: string | null;
}

export interface Subscription {
  id: number;
  tier: string;
  price_per_month: number;
  billing_cycle_start: string;
  billing_cycle_end?: string | null;
  status: string;
  seats: number;
}

export interface Plan {
  slug: string;
  name: string;
  price_per_month: number;
  description: string;
}

export interface Dashboard {
  active_contracts: number;
  total_seekers: number;
  pending_hitl: number;
  matches_this_week: number;
  avg_match_score: number;
  tier_a_matches: number;
  recent_matches: Array<{
    id: number;
    score: number;
    tier: string;
    status: string;
    seeker_name?: string | null;
    contract_title?: string | null;
    hitl_required: boolean;
  }>;
}

export interface Interview {
  id: number;
  agency_id: number;
  contract_id: number;
  seeker_id: number;
  match_id: number | null;
  scheduled_at: string | null;
  duration_minutes: number;
  interview_type: string;
  status: string;
  interviewer_name: string | null;
  interviewer_email: string | null;
  location: string | null;
  meeting_link: string | null;
  feedback: string | null;
  rating: number | null;
  outcome: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface Note {
  id: number;
  agency_id: number;
  user_id: number;
  entity_type: string;
  entity_id: number;
  content: string;
  is_pinned: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface Tag {
  id: number;
  agency_id: number;
  name: string;
  color: string;
}

export interface AppNotification {
  id: number;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  read_at: string | null;
  related_entity_type: string | null;
  related_entity_id: number | null;
  action_url: string | null;
  created_at: string | null;
}

export interface AgencySettings {
  id: number;
  agency_id: number;
  email_from_name: string | null;
  email_from_address: string | null;
  email_signature: string | null;
  whatsapp_number: string | null;
  telegram_bot_token: string | null;
  default_currency: string;
  timezone: string;
  notification_preferences: Record<string, boolean>;
  branding_logo_url: string | null;
  branding_primary_color: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface TeamMember {
  id: number;
  email: string;
  name: string;
  role: string;
  phone: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface EnhancedDashboard {
  active_contracts: number;
  total_seekers: number;
  pending_hitl: number;
  matches_this_week: number;
  avg_match_score: number;
  tier_a_matches: number;
  pipeline_distribution: Record<string, number>;
  tier_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
  recent_matches: { id: number; score: number; tier: string; status: string; contract_id: number; seeker_id: number; created_at: string | null }[];
}

export interface TimelinePoint {
  date: string;
  created: number;
  placed: number;
  rejected: number;
}