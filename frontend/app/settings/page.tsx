import { ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { getHealth, getProviderStatus, getSyncStatus } from "@/lib/api";
import { userFacingError } from "@/lib/errors";
import { capabilityLabel, connectionStateLabel, formatDateTime } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

const providers = [
  { name: "Mock", status: "available" },
          { name: "Workable", status: "read-only SPI mirror" },
  { name: "Dover", status: "planned" },
  { name: "Greenhouse", status: "planned" },
  { name: "Lever", status: "planned" },
  { name: "Ashby", status: "planned" },
];

export default async function SettingsPage() {
  const result = await loadPageData(() =>
    Promise.all([getHealth(), getProviderStatus(), getSyncStatus()]),
  );
  if (!result.ok) {
    return (
      <div>
        <PageHeader title="Settings" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const [health, provider, sync] = result.data;
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Connection and mirror status only. Tokens never appear in this UI."
      />

      <section className="mb-6 max-w-2xl rounded-md border border-stone-200 bg-white px-4 py-4 text-sm">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">Runtime</h2>
        <dl className="space-y-2">
          <Row label="Current provider" value={provider.provider} />
          <Row label="Account" value={sync.connection?.account_name ?? provider.account_name ?? "—"} />
          <Row label="Connection" value={connectionStateLabel(sync.connection_state)} />
          <Row label="Configured" value={provider.configured ? "Yes" : "No"} />
          <Row
            label="Database mirror"
            value={`${sync.counts.jobs} jobs · ${sync.counts.candidates} candidates · ${sync.counts.applications} applications`}
          />
          <Row label="Last full sync" value={formatDateTime(sync.last_full_sync_at)} />
          <Row label="Last incremental sync" value={formatDateTime(sync.last_incremental_sync_at)} />
          <Row label="Last successful sync" value={formatDateTime(sync.last_successful_sync_at)} />
          <Row
            label="Current sync status"
            value={sync.current_sync_status?.replaceAll("_", " ") ?? sync.last_run?.status.replaceAll("_", " ") ?? "—"}
          />
          <Row label="Local database" value="SQLite (DATABASE_URL)" />
          <Row label="Dry run" value={health.dry_run ? "On" : "Off"} />
          <Row label="AI provider" value="None" />
          <Row label="LLM API required" value="No" />
          <Row label="Official MCPs" value="Managed externally" />
          <Row label="Backend API" value={apiBase} />
        </dl>
        <p className="mt-4 text-sm leading-6 text-stone-600">
          ATS Mirror does not require an LLM. AI agents can manage ATS systems separately using
          their official MCP integrations.
        </p>
      </section>

      <section className="mb-6 max-w-2xl rounded-md border border-stone-200 bg-white px-4 py-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">Read capabilities</h2>
        <ul className="grid gap-1 sm:grid-cols-2">
          {provider.capabilities.map((capability) => (
            <li key={capability} className="text-sm text-stone-700">
              <span className="font-mono text-[13px]">{capabilityLabel(capability)}</span>
              <span className="ml-2 text-emerald-700" aria-label="supported">
                ✓
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="mb-6 max-w-2xl rounded-md border border-stone-200 bg-white px-4 py-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">Connections</h2>
        <p className="mb-3 text-sm leading-6 text-stone-600">
          Each ATS account is an isolated mirror. Dover and additional Workable accounts can be
          added later without mixing rows.
        </p>
        <ul className="space-y-2 text-sm">
          {(sync.connections ?? (sync.connection ? [sync.connection] : [])).map((item) => (
            <li key={item.id} className="flex items-center justify-between">
              <span className="text-stone-800">
                {item.account_name ?? item.external_account_id ?? item.provider}
              </span>
              <span className="capitalize text-stone-500">{item.provider}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="max-w-2xl rounded-md border border-stone-200 bg-white px-4 py-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-900">Supported providers</h2>
        <ul className="space-y-2 text-sm">
          {providers.map((item) => (
            <li key={item.name} className="flex items-center justify-between">
              <span className="text-stone-800">{item.name}</span>
              <span className="text-stone-500">{item.status}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-stone-500">{label}</dt>
      <dd className="text-right font-medium text-stone-800">{value}</dd>
    </div>
  );
}
