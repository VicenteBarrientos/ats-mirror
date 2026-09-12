import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { JobStatusBadge, StageBadge } from "@/components/Badges";
import { DataTable, RowLink } from "@/components/DataTable";
import { EmptyState, ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { getCandidates, getJob } from "@/lib/api";
import { ApiError, userFacingError } from "@/lib/errors";
import { dash, formatDate, lastActivity } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const result = await loadPageData(() => Promise.all([getJob(id), getCandidates(id)]));
  if (!result.ok) {
    if (result.error instanceof ApiError && result.error.status === 404) {
      notFound();
    }
    return (
      <div>
        <PageHeader title="Job" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const [job, candidates] = result.data;

    return (
      <div>
        <PageHeader
          title={job.title}
          description={`${dash(job.department)} · ${dash(job.location)}`}
        />

        <section className="mb-6 grid gap-4 rounded-md border border-stone-200 bg-white px-4 py-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Meta label="Status" value={<JobStatusBadge status={job.status} />} />
          <Meta label="Department" value={dash(job.department)} />
          <Meta label="Location" value={dash(job.location)} />
          <Meta label="Created" value={formatDate(job.created_at)} />
        </section>

        {job.description ? (
          <section className="mb-6">
            <h2 className="mb-2 text-sm font-semibold text-stone-800">Description</h2>
            <p className="max-w-3xl text-sm leading-6 text-stone-600">{job.description}</p>
          </section>
        ) : null}

        <section>
          <h2 className="mb-2 text-sm font-semibold text-stone-800">Candidates for this job</h2>
          {candidates.length === 0 ? (
            <EmptyState
              title="No candidates found for this job."
              message="When people apply, they will show up here."
            />
          ) : (
            <DataTable headers={["Name", "Headline", "Location", "Stage", "Last activity"]}>
              {candidates.map((candidate) => (
                <tr key={candidate.id} className="hover:bg-stone-50">
                  <td className="px-3 py-2">
                    <RowLink href={`/candidates/${candidate.id}`}>{candidate.name}</RowLink>
                  </td>
                  <td className="px-3 py-2 text-stone-600">{dash(candidate.headline)}</td>
                  <td className="px-3 py-2 text-stone-600">{dash(candidate.location)}</td>
                  <td className="px-3 py-2">
                    <StageBadge stage={candidate.current_stage} />
                  </td>
                  <td className="px-3 py-2 text-stone-500">{lastActivity(candidate)}</td>
                </tr>
              ))}
            </DataTable>
          )}
        </section>
      </div>
    );
}

function Meta({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-stone-500">{label}</p>
      <div className="mt-1 text-stone-800">{value}</div>
    </div>
  );
}
