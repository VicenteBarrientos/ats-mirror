import { ApiError } from "./errors";
import type {
  Candidate,
  CandidateDetail,
  Health,
  Job,
  ProviderStatus,
  SyncRun,
  SyncStatus,
} from "./types";

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiError("ATS Mirror API is unavailable.", 0, true);
  }

  if (response.status === 404) {
    throw new ApiError("Not found.", 404);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("Malformed response from ATS Mirror API.", response.status);
  }

  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `Request failed (${response.status}).`;
    throw new ApiError(detail, response.status);
  }

  return payload as T;
}

async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export async function getHealth(): Promise<Health> {
  const data = await apiGet<Health>("/api/health");
  if (!data || typeof data.provider !== "string") {
    throw new ApiError("Malformed response from ATS Mirror API.");
  }
  return data;
}

export async function getHealthSafe(): Promise<Health | null> {
  try {
    return await getHealth();
  } catch {
    return null;
  }
}

export async function getProviderStatus(): Promise<ProviderStatus> {
  return apiGet<ProviderStatus>("/api/provider/status");
}

export async function getJobs(): Promise<Job[]> {
  const data = await apiGet<Job[]>("/api/jobs");
  if (!Array.isArray(data)) {
    throw new ApiError("Malformed response from ATS Mirror API.");
  }
  return data;
}

export async function getJob(id: string): Promise<Job> {
  return apiGet<Job>(`/api/jobs/${encodeURIComponent(id)}`);
}

export async function getCandidates(jobId?: string): Promise<Candidate[]> {
  const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
  const data = await apiGet<Candidate[]>(`/api/candidates${query}`);
  if (!Array.isArray(data)) {
    throw new ApiError("Malformed response from ATS Mirror API.");
  }
  return data;
}

export async function getCandidate(id: string): Promise<CandidateDetail> {
  return apiGet<CandidateDetail>(`/api/candidates/${encodeURIComponent(id)}`);
}

export async function getSyncStatus(): Promise<SyncStatus> {
  return apiGet<SyncStatus>("/api/sync/status");
}

export async function postSync(): Promise<SyncRun> {
  return apiRequest<SyncRun>("/api/sync", { method: "POST" });
}

export async function postIncrementalSync(): Promise<SyncRun> {
  return apiRequest<SyncRun>("/api/sync/incremental", { method: "POST" });
}

export function candidatesExportUrl(): string {
  return `${apiBase()}/api/export/candidates.csv`;
}

export async function getSyncRuns(): Promise<SyncRun[]> {
  const data = await apiGet<SyncRun[]>("/api/sync/runs");
  if (!Array.isArray(data)) {
    throw new ApiError("Malformed response from ATS Mirror API.");
  }
  return data;
}

export async function getSyncRun(id: string): Promise<SyncRun> {
  return apiGet<SyncRun>(`/api/sync/runs/${encodeURIComponent(id)}`);
}
