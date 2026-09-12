import { JobStatusBadge, StageBadge } from "@/components/Badges";
import { DataTable, RowLink } from "@/components/DataTable";
import { EmptyState, ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { SyncNowButton } from "@/components/SyncNowButton";
import { getCandidates, getHealth, getJobs, getProviderStatus, getSyncStatus } from "@/lib/api";
import { userFacingError } from "@/lib/errors";
import { dash, connectionStateLabel, formatDateTime, lastActivity } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const result = await loadPageData(() =>
    Promise.all([getHealth(), getProviderStatus(), getJobs(), getCandidates(), getSyncStatus()]),
  );
  if (!result.ok) {
    return (
      <div>
        <PageHeader title="Dashboard" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const [health, provider, jobs, candidates, sync] = result.data;
  const openJobs = jobs.filter((job) => job.status === "open");
  const recent = [...candidates]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 6);
  const lastRun = sync.last_run;
  const counts = sync.counts;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Local mirrored copy. Pages read SQLite; sync is explicit."
        actions={<SyncNowButton />}
      />

      <section className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <SummaryCard label="Jobs" value={String(counts.jobs)} />
        <SummaryCard label="Candidates" value={String(counts.candidates)} />
        <SummaryCard label="Applications" value={String(counts.applications)} />
        <SummaryCard label="Events" value={String(counts.events)} />
        <SummaryCard label="Stages" value={String(counts.stages ?? 0)} />
        <SummaryCard label="Files metadata" value={String(counts.files ?? 0)} />
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-5">
          <section>
            <h2 className="mb-2 text-sm font-semibold text-stone-800">Recent candidates</h2>
            {recent.length === 0 ? (
              <EmptyState
                title="No mirrored candidates"
                message="Run Sync now to copy recruiting data into the local database."
              />
            ) : (
              <DataTable headers={["Candidate", "Job", "Stage", "Last activity"]}>
                {recent.map((candidate) => (
                  <tr key={candidate.id} className="hover:bg-stone-50">
                    <td className="px-3 py-2">
                      <RowLink href={`/candidates/${candidate.id}`}>{candidate.name}</RowLink>
                    </td>
                    <td className="px-3 py-2 text-stone-600">{dash(candidate.job_title)}</td>
                    <td className="px-3 py-2">
                      <StageBadge stage={candidate.current_stage} />
                    </td>
                    <td className="px-3 py-2 text-stone-500">{lastActivity(candidate)}</td>
                  </tr>
                ))}
              </DataTable>
            )}
          </section>

          <section>
            <h2 className="mb-2 text-sm font-semibold text-stone-800">Open jobs</h2>
            {openJobs.length === 0 ? (
              <EmptyState title="No open jobs" message="There are currently no open mirrored roles." />
            ) : (
              <DataTable headers={["Job", "Department", "Location", "Status"]}>
                {openJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-stone-50">
                    <td className="px-3 py-2">
                      <RowLink href={`/jobs/${job.id}`}>{job.title}</RowLink>
                    </td>
                    <td className="px-3 py-2 text-stone-600">{dash(job.department)}</td>
                    <td className="px-3 py-2 text-stone-600">{dash(job.location)}</td>
                    <td className="px-3 py-2">
                      <JobStatusBadge status={job.status} />
                    </td>
                  </tr>
                ))}
              </DataTable>
            )}
          </section>
        </div>

        <section className="space-y-5">
          <div>
            <h2 className="mb-2 text-sm font-semibold text-stone-800">Mirror status</h2>
            <dl className="rounded-md border border-stone-200 bg-white px-4 py-3 text-sm">
              <StatusRow
                label="Current connection"
                value={sync.connection?.account_name ?? provider.account_name ?? provider.provider}
              />
              <StatusRow label="Provider" value={provider.provider} />
              <StatusRow
                label="Account"
                value={sync.connection?.account_name ?? provider.account_name ?? "—"}
              />
              <StatusRow
                label="Connection status"
                value={connectionStateLabel(sync.connection_state)}
              />
              <StatusRow label="Last full sync" value={formatDateTime(sync.last_full_sync_at)} />
              <StatusRow
                label="Last incremental sync"
                value={formatDateTime(sync.last_incremental_sync_at)}
              />
              <StatusRow
                label="Last successful sync"
                value={formatDateTime(sync.last_successful_sync_at)}
              />
              <StatusRow
                label="Current sync status"
                value={
                  sync.current_sync_status?.replaceAll("_", " ") ??
                  lastRun?.status.replaceAll("_", " ") ??
                  "—"
                }
              />
              <StatusRow label="Dry run" value={health.dry_run ? "On" : "Off"} />
              <StatusRow label="AI" value="Not used" />
            </dl>
          </div>
          {lastRun ? (
            <div>
              <h2 className="mb-2 text-sm font-semibold text-stone-800">Last sync</h2>
              <dl className="rounded-md border border-stone-200 bg-white px-4 py-3 text-sm">
                <StatusRow label="When" value={formatDateTime(lastRun.completed_at ?? lastRun.started_at)} />
                <StatusRow label="Jobs fetched" value={String(lastRun.jobs_seen)} />
                <StatusRow label="Candidates fetched" value={String(lastRun.candidates_seen)} />
                <StatusRow label="Applications fetched" value={String(lastRun.applications_seen)} />
                <StatusRow label="Stages fetched" value={String(lastRun.stages_seen ?? 0)} />
                <StatusRow label="Events fetched" value={String(lastRun.events_seen)} />
                <StatusRow label="Files fetched" value={String(lastRun.files_seen ?? 0)} />
                <StatusRow label="Canonical created" value={String(lastRun.created_count)} />
                <StatusRow label="Canonical updated" value={String(lastRun.updated_count)} />
                <StatusRow label="Canonical unchanged" value={String(lastRun.unchanged_count)} />
                <StatusRow label="Errors" value={String(lastRun.error_count)} />
              </dl>
              <p className="mt-2 text-xs leading-5 text-stone-500">
                Fetched counts are source objects from the ATS this run. Created/updated/unchanged
                count canonical SQLite rows (jobs, candidates, applications, stages, events, file
                metadata). Stages and files are included there, which is why unchanged can exceed
                jobs+candidates+applications+events.
              </p>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-stone-200 bg-white px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight text-stone-900">{value}</p>
    </div>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-stone-100 py-2 last:border-b-0">
      <dt className="text-stone-500">{label}</dt>
      <dd className="font-medium capitalize text-stone-800">{value}</dd>
    </div>
  );
}
