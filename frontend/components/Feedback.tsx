export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-md border border-dashed border-stone-300 bg-white px-4 py-10 text-center">
      <p className="text-sm font-medium text-stone-800">{title}</p>
      <p className="mt-1 text-sm text-stone-500">{message}</p>
    </div>
  );
}

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900"
    >
      {message}
    </div>
  );
}
