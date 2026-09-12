import { DataTable, RowLink } from "@/components/DataTable";
import { EmptyState, ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { SyncNowButton } from "@/components/SyncNowButton";
import { getSyncRuns } from "@/lib/api";
import { userFacingError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

export default async function SyncHistoryPage() {
  const result = await loadPageData(() => getSyncRuns());
  if (!result.ok) {
    return (
      <div>
        <PageHeader title="Sync history" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const runs = result.data;

  return (
    <div>
      <PageHeader
        title="Sync history"
        description="Read-only copies into the local database. Sync changes is the ordinary action; full sync re-reads every supported collection."
        actions={<SyncNowButton />}
      />
      {runs.length === 0 ? (
        <EmptyState title="No sync runs" message="Press Sync now to create the first local mirror." />
      ) : (
        <DataTable
          headers={[
            "Timestamp",
            "Connection",
            "Provider",
            "Sync type",
            "Status",
            "Duration",
            "Jobs fetched",
            "Candidates fetched",
            "Applications fetched",
            "Events fetched",
            "Created",
            "Updated",
            "Unchanged",
            "Errors",
          ]}
        >
          {runs.map((run) => (
            <tr key={run.id} className="hover:bg-stone-50">
              <td className="px-3 py-2">
                <RowLink href={`/sync/${run.id}`}>{formatDateTime(run.started_at)}</RowLink>
              </td>
              <td className="px-3 py-2 text-stone-600">{run.connection_name ?? "—"}</td>
              <td className="px-3 py-2 capitalize text-stone-600">{run.provider}</td>
              <td className="px-3 py-2 capitalize text-stone-600">{run.sync_type}</td>
              <td className="px-3 py-2 capitalize text-stone-700">{run.status.replaceAll("_", " ")}</td>
              <td className="px-3 py-2 text-stone-500">{duration(run.started_at, run.completed_at)}</td>
              <td className="px-3 py-2 text-stone-600">{run.jobs_seen}</td>
              <td className="px-3 py-2 text-stone-600">{run.candidates_seen}</td>
              <td className="px-3 py-2 text-stone-600">{run.applications_seen}</td>
              <td className="px-3 py-2 text-stone-600">{run.events_seen}</td>
              <td className="px-3 py-2 text-stone-600">{run.created_count}</td>
              <td className="px-3 py-2 text-stone-600">{run.updated_count}</td>
              <td className="px-3 py-2 text-stone-600">{run.unchanged_count}</td>
              <td className="px-3 py-2 text-stone-600">{run.error_count}</td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  );
}

function duration(started: string, completed: string | null): string {
  if (!completed) return "—";
  const ms = Date.parse(completed) - Date.parse(started);
  if (Number.isNaN(ms) || ms < 0) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}
