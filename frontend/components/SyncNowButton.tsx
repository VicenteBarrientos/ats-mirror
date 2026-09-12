"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { postIncrementalSync, postSync } from "@/lib/api";
import { userFacingError } from "@/lib/errors";

export function SyncNowButton({ label = "Sync changes" }: { label?: string }) {
  return <SyncControls primaryLabel={label} />;
}

export function SyncControls({ primaryLabel = "Sync changes" }: { primaryLabel?: string }) {
  const router = useRouter();
  const [pending, setPending] = useState<"incremental" | "full" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(kind: "incremental" | "full") {
    setPending(kind);
    setError(null);
    try {
      if (kind === "incremental") {
        await postIncrementalSync();
      } else {
        await postSync();
      }
      router.refresh();
    } catch (caught) {
      setError(userFacingError(caught));
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => void run("incremental")}
          disabled={pending !== null}
          className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
        >
          {pending === "incremental" ? "Syncing…" : primaryLabel}
        </button>
        <button
          type="button"
          onClick={() => void run("full")}
          disabled={pending !== null}
          className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-700 disabled:opacity-60"
        >
          {pending === "full" ? "Syncing…" : "Full sync"}
        </button>
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
