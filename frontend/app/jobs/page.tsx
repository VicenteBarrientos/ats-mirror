import Link from "next/link";
import { JobStatusBadge } from "@/components/Badges";
import { DataTable, RowLink } from "@/components/DataTable";
import { EmptyState, ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { getJobs } from "@/lib/api";
import { userFacingError } from "@/lib/errors";
import { dash, formatDate } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

const filters: { label: string; value: string }[] = [
  { label: "All", value: "all" },
  { label: "Open", value: "open" },
  { label: "Closed", value: "closed" },
];

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status = "all" } = await searchParams;
  const result = await loadPageData(() => getJobs());
  if (!result.ok) {
    return (
      <div>
        <PageHeader title="Jobs" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const jobs = result.data;
  const visible = jobs.filter((job) => {
    if (status === "open" || status === "closed") {
      return job.status === status;
    }
    return true;
  });

    return (
      <div>
        <PageHeader title="Jobs" description="Roles currently synced from the ATS." />
        <div className="mb-4 flex gap-1" role="tablist" aria-label="Job status">
          {filters.map((filter) => {
            const href = filter.value === "all" ? "/jobs" : `/jobs?status=${filter.value}`;
            const active =
              status === filter.value || (filter.value === "all" && status !== "open" && status !== "closed");
            return (
              <Link
                key={filter.value}
                href={href}
                className={
                  active
                    ? "rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white"
                    : "rounded-md px-3 py-1.5 text-sm text-stone-600 hover:bg-white"
                }
              >
                {filter.label}
              </Link>
            );
          })}
        </div>
        {visible.length === 0 ? (
          <EmptyState
            title="No jobs"
            message="No mirrored jobs match this filter. Sync from the dashboard if the database is empty."
          />
        ) : (
          <DataTable headers={["Title", "Department", "Location", "Status", "Created", "Candidates"]}>
            {visible.map((job) => (
              <tr key={job.id} className="hover:bg-stone-50">
                <td className="px-3 py-2">
                  <RowLink href={`/jobs/${job.id}`}>{job.title}</RowLink>
                </td>
                <td className="px-3 py-2 text-stone-600">{dash(job.department)}</td>
                <td className="px-3 py-2 text-stone-600">{dash(job.location)}</td>
                <td className="px-3 py-2">
                  <JobStatusBadge status={job.status} />
                </td>
                <td className="px-3 py-2 text-stone-500">{formatDate(job.created_at)}</td>
                <td className="px-3 py-2 text-stone-600">{job.candidate_count ?? "—"}</td>
              </tr>
            ))}
          </DataTable>
        )}
      </div>
    );
}
