import type { Candidate, EventType } from "./types";

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const dateTimeFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return dateFormat.format(date);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return dateTimeFormat.format(date);
}

export function formatEventType(type: EventType | string | null | undefined): string {
  if (!type) return "—";
  return type.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

export function lastActivity(candidate: Candidate): string {
  return formatDateTime(candidate.last_event_at ?? candidate.created_at);
}

export function capabilityLabel(capability: string): string {
  return capability.toUpperCase();
}

export function dash(value: string | null | undefined): string {
  return value?.trim() ? value : "—";
}

export function connectionStateLabel(state: string | null | undefined): string {
  switch (state) {
    case "not_configured":
      return "Not configured";
    case "disconnected":
      return "Disconnected";
    case "syncing":
      return "Syncing";
    case "last_sync_succeeded":
      return "Last sync succeeded";
    case "last_sync_failed":
      return "Last sync failed";
    case "connected":
      return "Connected";
    default:
      return state ? state.replaceAll("_", " ") : "Unknown";
  }
}
