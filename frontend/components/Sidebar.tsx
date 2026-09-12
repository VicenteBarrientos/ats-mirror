"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/candidates", label: "Candidates" },
  { href: "/sync", label: "Sync history" },
  { href: "/automations", label: "Automations" },
  { href: "/settings", label: "Settings" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 shrink-0 flex-col bg-[#1b2421] text-stone-100">
      <div className="border-b border-white/10 px-4 py-4">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-[#c9a227]">
          ATS Mirror
        </p>
        <p className="mt-0.5 text-sm font-semibold tracking-tight">Any ATS</p>
      </div>
      <nav aria-label="Main" className="flex flex-1 flex-col gap-0.5 p-2">
        {items.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "rounded-md bg-white/10 px-3 py-2 text-sm font-medium text-white"
                  : "rounded-md px-3 py-2 text-sm text-stone-300 hover:bg-white/5 hover:text-white"
              }
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <p className="px-4 py-3 text-[11px] leading-4 text-[#8b958f]">
        One recruiting data layer. The ATS stays the system of record.
      </p>
    </aside>
  );
}
