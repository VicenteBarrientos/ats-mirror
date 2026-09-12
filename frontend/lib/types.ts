/** Types match FastAPI OpenAPI (`/openapi.json`) plus list-view enrichment fields. */

export type JobStatus = "open" | "closed" | "draft" | "archived";

export type ApplicationStatus = "active" | "hired" | "rejected" | "withdrawn";

export type EventType =
  | "candidate_created"
  | "stage_changed"
  | "note_added"
  | "interview_scheduled"
  | "feedback_submitted"
  | "other";

export interface Job {
  id: string;
  external_id: string;
  title: string;
  department: string | null;
  location: string | null;
  status: JobStatus;
  description: string | null;
  created_at: string;
  candidate_count: number | null;
}

export interface Candidate {
  id: string;
  external_id: string;
  name: string;
  headline: string | null;
  location: string | null;
  email: string | null;
  current_stage: string | null;
  created_at: string;
  job_id: string | null;
  job_title: string | null;
  last_event_at: string | null;
  last_event_type: EventType | null;
}

export interface Application {
  id: string;
  external_id: string;
  candidate_id: string;
  job_id: string;
  stage: string | null;
  status: ApplicationStatus;
}

export interface RecruitingEvent {
  id: string;
  external_id: string;
  candidate_id: string | null;
  job_id: string | null;
  event_type: EventType;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface CandidateDetail extends Candidate {
  applications: Application[];
  events: RecruitingEvent[];
}

export interface AtsConnection {
  id: string;
  provider: string;
  external_account_id: string | null;
  account_name: string | null;
}

export type ConnectionState =
  | "not_configured"
  | "disconnected"
  | "connected"
  | "syncing"
  | "last_sync_succeeded"
  | "last_sync_failed";

export interface Health {
  status: string;
  provider: string;
  provider_ok: boolean;
  provider_message: string;
  capabilities: string[];
  database: string;
  dry_run: boolean;
  ai_enabled: boolean;
  ai_provider: string | null;
  configured?: boolean;
  connection_state?: ConnectionState;
  connection?: AtsConnection;
  last_successful_sync_at: string | null;
  last_full_sync_at?: string | null;
  last_incremental_sync_at?: string | null;
  last_attempted_sync_at?: string | null;
  last_sync_status: string | null;
  mirror: MirrorCounts;
}

export interface MirrorCounts {
  jobs: number;
  candidates: number;
  applications: number;
  events: number;
  stages?: number;
  files?: number;
  raw_objects?: number;
}

export interface ProviderStatus {
  provider: string;
  ok: boolean;
  message: string;
  capabilities: string[];
  dry_run: boolean;
  configured: boolean;
  ai_provider: string | null;
  llm_api_required: boolean;
  account_id?: string | null;
  account_name?: string | null;
}

export type SyncRunStatus = "running" | "completed" | "completed_with_errors" | "failed";

export interface SyncError {
  id: string;
  sync_run_id: string;
  provider: string;
  object_type: string;
  external_id: string | null;
  error_type: string;
  error_category?: string;
  http_status?: number | null;
  message: string;
  timestamp: string;
}

export interface SyncRun {
  id: string;
  connection_id?: string | null;
  connection_name?: string | null;
  provider: string;
  sync_type: string;
  started_at: string;
  completed_at: string | null;
  status: SyncRunStatus;
  jobs_seen: number;
  candidates_seen: number;
  applications_seen: number;
  events_seen: number;
  stages_seen?: number;
  files_seen?: number;
  source_objects_fetched?: number;
  raw_objects_created?: number;
  raw_objects_updated?: number;
  raw_objects_unchanged?: number;
  canonical_records_created?: number;
  canonical_records_updated?: number;
  canonical_records_unchanged?: number;
  created_count: number;
  updated_count: number;
  unchanged_count: number;
  error_count: number;
  error_summary: string | null;
  errors: SyncError[];
}

export interface SyncStatus {
  provider: string;
  configured?: boolean;
  connection_ok: boolean;
  connection_message: string;
  connection_state?: ConnectionState;
  connection?: AtsConnection;
  connections?: AtsConnection[];
  last_successful_sync_at: string | null;
  last_full_sync_at?: string | null;
  last_incremental_sync_at?: string | null;
  last_attempted_sync_at?: string | null;
  current_sync_status?: string | null;
  watermarks?: Record<string, { last_successful_watermark: string | null }>;
  last_run: SyncRun | null;
  counts: MirrorCounts;
  metric_notes?: Record<string, string>;
  ai_provider: null;
  llm_api_required: boolean;
}
