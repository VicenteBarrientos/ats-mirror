import { PageHeader } from "@/components/PageHeader";

export default function AutomationsPage() {
  return (
    <div>
      <PageHeader
        title="Automations"
        description="Workflows are out of scope for the local ATS mirror."
      />
      <article className="max-w-2xl rounded-md border border-stone-200 bg-white px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-stone-900">ATS writes and AI briefs</h2>
          <span className="rounded-sm border border-stone-200 bg-stone-50 px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-stone-600">
            Not in this product
          </span>
        </div>
        <p className="mt-2 text-sm leading-6 text-stone-600">
          ATS Mirror copies recruiting data into a local database. It does not move candidates,
          add notes, or score people. Interactive ATS actions belong in official Workable or Dover
          MCP integrations used by AI agents separately.
        </p>
        <p className="mt-3 text-sm text-stone-500">No automations are active in Milestone 3.</p>
      </article>
    </div>
  );
}
