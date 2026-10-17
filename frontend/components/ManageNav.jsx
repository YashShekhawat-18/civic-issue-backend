"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/admin/manage/workers", label: "Workers" },
  { href: "/admin/manage/departments", label: "Departments" },
  { href: "/admin/manage/categories", label: "Categories" },
  { href: "/admin/manage/audit", label: "Activity log" },
];

export default function ManageNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Manage" className="mb-6 flex gap-1 overflow-x-auto rounded-xl bg-white p-1 ring-1 ring-line">
      {TABS.map((t) => {
        const active = pathname.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            aria-current={active ? "page" : undefined}
            className={`whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-semibold ${active ? "bg-asphalt text-white" : "text-asphalt-soft hover:bg-concrete"}`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
