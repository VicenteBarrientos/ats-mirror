import type { ReactNode } from "react";
import Link from "next/link";

export function DataTable({
  headers,
  children,
}: {
  headers: string[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-stone-200 bg-white">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-stone-200 bg-stone-50 text-[11px] uppercase tracking-wide text-stone-500">
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col" className="px-3 py-2 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">{children}</tbody>
      </table>
    </div>
  );
}

export function RowLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className="font-medium text-stone-900 hover:underline">
      {children}
    </Link>
  );
}
