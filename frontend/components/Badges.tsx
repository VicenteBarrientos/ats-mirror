import type { JobStatus } from "@/lib/types";

const jobStyles: Record<JobStatus, string> = {
  open: "border-emerald-200 bg-emerald-50 text-emerald-900",
  closed: "border-stone-200 bg-stone-100 text-stone-700",
  draft: "border-sky-200 bg-sky-50 text-sky-900",
  archived: "border-stone-200 bg-stone-50 text-stone-500",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-flex rounded-sm border px-1.5 py-0.5 text-[11px] font-medium capitalize ${jobStyles[status]}`}
    >
      {status}
    </span>
  );
}

export function StageBadge({ stage }: { stage: string | null }) {
  if (!stage) {
    return <span className="text-stone-400">—</span>;
  }
  return (
    <span className="inline-flex rounded-sm border border-stone-200 bg-white px-1.5 py-0.5 text-[11px] font-medium text-stone-700">
      {stage}
    </span>
  );
}
