import { StageBadge } from "@/components/Badges";
import { DataTable, RowLink } from "@/components/DataTable";
import { EmptyState, ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { candidatesExportUrl, getCandidates } from "@/lib/api";
import { userFacingError } from "@/lib/errors";
import { dash, lastActivity } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

export default async function CandidatesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; stage?: string }>;
}) {
  const { q = "", stage = "" } = await searchParams;
  const query = q.trim().toLowerCase();
  const result = await loadPageData(() => getCandidates());
  if (!result.ok) {
    return (
      <div>
        <PageHeader title="Candidates" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const candidates = result.data;
  const stages = [...new Set(candidates.map((item) => item.current_stage).filter(Boolean))] as string[];
  const visible = candidates.filter((candidate) => {
    const haystack = [candidate.name, candidate.headline ?? "", candidate.job_title ?? ""]
      .join(" ")
      .toLowerCase();
    const matchesQuery = query.length === 0 || haystack.includes(query);
    const matchesStage = stage.length === 0 || candidate.current_stage === stage;
    return matchesQuery && matchesStage;
  });

    return (
      <div>
        <PageHeader
          title="Candidates"
          description="People currently mirrored into the local database."
          actions={
            <a
              href={candidatesExportUrl()}
              className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-700"
            >
              Export CSV
            </a>
          }
        />
        <form method="get" className="mb-4 flex flex-wrap gap-2" role="search">
          <label className="sr-only" htmlFor="candidate-search">
            Search candidates
          </label>
          <input
            id="candidate-search"
            name="q"
            defaultValue={q}
            placeholder="Search name, headline, job"
            className="w-64 rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-stone-500"
          />
          <label className="sr-only" htmlFor="stage-filter">
            Stage
          </label>
          <select
            id="stage-filter"
            name="stage"
            defaultValue={stage}
            className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-stone-500"
          >
            <option value="">All stages</option>
            {stages.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white"
          >
            Filter
          </button>
        </form>
        {visible.length === 0 ? (
          <EmptyState title="No candidates" message="No candidates match this search." />
        ) : (
          <DataTable headers={["Candidate", "Job", "Headline", "Location", "Stage", "Last activity"]}>
            {visible.map((candidate) => (
              <tr key={candidate.id} className="hover:bg-stone-50">
                <td className="px-3 py-2">
                  <RowLink href={`/candidates/${candidate.id}`}>{candidate.name}</RowLink>
                </td>
                <td className="px-3 py-2 text-stone-600">{dash(candidate.job_title)}</td>
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
      </div>
    );
}
