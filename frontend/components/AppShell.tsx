import type { ReactNode } from "react";
import { Sidebar } from "@/components/Sidebar";
import { StatusStrip } from "@/components/StatusStrip";
import type { Health } from "@/lib/types";

export function AppShell({
  health,
  children,
}: {
  health: Health | null;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-full">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <StatusStrip health={health} />
        <main className="flex-1 px-6 py-5">{children}</main>
      </div>
    </div>
  );
}
