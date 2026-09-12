import type { Health } from "@/lib/types";
import { connectionStateLabel } from "@/lib/format";

export function StatusStrip({ health }: { health: Health | null }) {
  const state = health?.connection_state;
  const connected = Boolean(health?.provider_ok && health.status === "ok" && state !== "not_configured");
  const provider = (health?.provider ?? "unknown").toUpperCase();
  const account = health?.connection?.account_name;
  const label = connectionStateLabel(state ?? (connected ? "connected" : "disconnected"));

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-stone-200 bg-white px-6 py-2.5 text-xs">
      <span
        className={
          connected
            ? "font-medium tracking-wide text-stone-700"
            : "font-medium tracking-wide text-red-700"
        }
      >
        {provider} ATS • {label}
      </span>
      {account ? <span className="text-stone-500">{account}</span> : null}
      {health?.dry_run ? (
        <span className="rounded-sm border border-amber-300 bg-amber-100 px-1.5 py-0.5 font-semibold uppercase tracking-wider text-amber-950">
          Dry run
        </span>
      ) : null}
      {health ? (
        <span className="text-stone-500">
          API {health.database === "ok" ? "healthy" : "degraded"}
        </span>
      ) : (
        <span className="text-red-700">ATS Mirror API is unavailable.</span>
      )}
    </div>
  );
}
