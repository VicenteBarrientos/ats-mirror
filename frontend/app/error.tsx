"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="max-w-lg">
      <h1 className="text-lg font-semibold text-stone-900">Something went wrong</h1>
      <p className="mt-2 text-sm text-stone-600">
        {error.message || "ATS Mirror API is unavailable."}
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white"
      >
        Try again
      </button>
    </div>
  );
}
