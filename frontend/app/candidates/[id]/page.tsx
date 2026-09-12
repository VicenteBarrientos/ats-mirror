import type { ReactNode } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { StageBadge } from "@/components/Badges";
import { DataTable } from "@/components/DataTable";
import { ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { getCandidate } from "@/lib/api";
import { ApiError, userFacingError } from "@/lib/errors";
import { dash, formatDateTime, formatEventType } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

export default async function CandidateDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const result = await loadPageData(() => getCandidate(id));
  if (!result.ok) {
    if (result.error instanceof ApiError && result.error.status === 404) {
      notFound();
    }
    return (
      <div>
        <PageHeader title="Candidate" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const candidate = result.data;

    return (
      <div>
        <PageHeader
          title={candidate.name}
          description={dash(candidate.headline)}
        />

        <section className="mb-6 grid gap-4 rounded-md border border-stone-200 bg-white px-4 py-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Meta label="Location" value={dash(candidate.location)} />
          <Meta label="Email" value={dash(candidate.email)} />
          <Meta label="Current stage" value={<StageBadge stage={candidate.current_stage} />} />
          <Meta
            label="Associated job"
            value={
              candidate.job_id ? (
                <Link className="font-medium hover:underline" href={`/jobs/${candidate.job_id}`}>
                  {dash(candidate.job_title)}
                </Link>
              ) : (
                dash(candidate.job_title)
              )
            }
          />
        </section>

        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-stone-800">Overview</h2>
          <p className="max-w-3xl text-sm leading-6 text-stone-600">
            {candidate.headline
              ? `${candidate.name} is in ${candidate.current_stage ?? "an unspecified stage"} for ${candidate.job_title ?? "an unspecified role"}.`
              : "No additional summary is available from the ATS."}
          </p>
        </section>

        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-stone-800">Applications</h2>
          {candidate.applications.length === 0 ? (
            <p className="text-sm text-stone-500">No applications on file.</p>
          ) : (
            <DataTable headers={["Job", "Stage", "Status"]}>
              {candidate.applications.map((application) => (
                <tr key={application.id}>
                  <td className="px-3 py-2 text-stone-800">
                    {application.job_id === candidate.job_id
                      ? dash(candidate.job_title)
                      : application.job_id}
                  </td>
                  <td className="px-3 py-2">
                    <StageBadge stage={application.stage} />
                  </td>
                  <td className="px-3 py-2 capitalize text-stone-600">{application.status}</td>
                </tr>
              ))}
            </DataTable>
          )}
        </section>

        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-stone-800">Timeline</h2>
          {candidate.events.length === 0 ? (
            <p className="text-sm text-stone-500">No recruiting events recorded.</p>
          ) : (
            <ol className="space-y-3 border-l border-stone-200 pl-4">
              {candidate.events.map((event) => (
                <li key={event.id} className="text-sm">
                  <p className="font-medium text-stone-800">{formatEventType(event.event_type)}</p>
                  <p className="text-stone-500">{formatDateTime(event.timestamp)}</p>
                  {event.metadata && Object.keys(event.metadata).length > 0 ? (
                    <p className="mt-0.5 text-stone-600">
                      {Object.entries(event.metadata)
                        .map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`)
                        .join(" · ")}
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="mb-6 rounded-md border border-dashed border-stone-300 bg-white px-4 py-4">
          <h2 className="text-sm font-semibold text-stone-800">Recruiter brief</h2>
          <p className="mt-1 text-sm text-stone-500">
            AI candidate briefing will appear here in a later milestone.
          </p>
        </section>

        <details className="rounded-md border border-stone-200 bg-white px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium text-stone-700">Developer data</summary>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-stone-500">Internal id</dt>
              <dd className="font-mono text-xs text-stone-700">{candidate.id}</dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-stone-500">External id</dt>
              <dd className="font-mono text-xs text-stone-700">{candidate.external_id}</dd>
            </div>
          </dl>
        </details>
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
