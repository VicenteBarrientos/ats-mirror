import { notFound } from "next/navigation";
import { DataTable } from "@/components/DataTable";
import { ErrorPanel } from "@/components/Feedback";
import { PageHeader } from "@/components/PageHeader";
import { getSyncRun } from "@/lib/api";
import { ApiError, userFacingError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { loadPageData } from "@/lib/load";

export const dynamic = "force-dynamic";

export default async function SyncRunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const result = await loadPageData(() => getSyncRun(id));
  if (!result.ok) {
    if (result.error instanceof ApiError && result.error.status === 404) {
      notFound();
    }
    return (
      <div>
        <PageHeader title="Sync run" />
        <ErrorPanel message={userFacingError(result.error)} />
      </div>
    );
  }
  const run = result.data;

  return (
    <div>
      <PageHeader
        title="Sync run"
        description={`${run.provider} · ${run.sync_type} · ${run.status.replaceAll("_", " ")}`}
      />
      <dl className="mb-6 max-w-xl rounded-md border border-stone-200 bg-white px-4 py-3 text-sm">
        <Row label="Started" value={formatDateTime(run.started_at)} />
        <Row label="Completed" value={formatDateTime(run.completed_at)} />
        <Row label="Jobs fetched" value={String(run.jobs_seen)} />
        <Row label="Candidates fetched" value={String(run.candidates_seen)} />
        <Row label="Applications fetched" value={String(run.applications_seen)} />
        <Row label="Stages fetched" value={String(run.stages_seen ?? 0)} />
        <Row label="Events fetched" value={String(run.events_seen)} />
        <Row label="Files fetched" value={String(run.files_seen ?? 0)} />
        <Row label="Source objects fetched" value={String(run.source_objects_fetched ?? 0)} />
        <Row label="Raw created" value={String(run.raw_objects_created ?? 0)} />
        <Row label="Raw updated" value={String(run.raw_objects_updated ?? 0)} />
        <Row label="Raw unchanged" value={String(run.raw_objects_unchanged ?? 0)} />
        <Row label="Canonical created" value={String(run.created_count)} />
        <Row label="Canonical updated" value={String(run.updated_count)} />
        <Row label="Canonical unchanged" value={String(run.unchanged_count)} />
        <Row label="Errors" value={String(run.error_count)} />
      </dl>
      {run.errors.length > 0 ? (
        <DataTable headers={["Time", "Object", "External ID", "Category", "Type", "Message"]}>
          {run.errors.map((item) => (
            <tr key={item.id}>
              <td className="px-3 py-2 text-stone-500">{formatDateTime(item.timestamp)}</td>
              <td className="px-3 py-2 text-stone-700">{item.object_type}</td>
              <td className="px-3 py-2 text-stone-600">{item.external_id ?? "—"}</td>
              <td className="px-3 py-2 text-stone-600">{item.error_category ?? "—"}</td>
              <td className="px-3 py-2 text-stone-600">{item.error_type}</td>
              <td className="px-3 py-2 text-stone-600">{item.message}</td>
            </tr>
          ))}
        </DataTable>
      ) : (
        <p className="text-sm text-stone-500">No object-level errors recorded.</p>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-stone-100 py-2 last:border-b-0">
      <dt className="text-stone-500">{label}</dt>
      <dd className="font-medium text-stone-800">{value}</dd>
    </div>
  );
}
