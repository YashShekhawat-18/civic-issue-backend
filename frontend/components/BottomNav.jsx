"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconFlag, IconHome, IconList, IconPin, IconPlus, IconCompass } from "./icons";

export const CITIZEN_TABS = [
  { href: "/citizen", label: "Home", Icon: IconHome, exact: true },
  { href: "/citizen/complaints", label: "My complaints", Icon: IconList },
  { href: "/citizen/report", label: "Report", Icon: IconPlus, primary: true },
  { href: "/citizen/nearby", label: "Nearby", Icon: IconCompass },
];

export const WORKER_TABS = [
  { href: "/worker", label: "Dashboard", Icon: IconHome, exact: true },
  { href: "/worker/tasks", label: "Tasks", Icon: IconList },
];

export const ADMIN_TABS = [
  { href: "/admin", label: "Dashboard", Icon: IconHome, exact: true },
  { href: "/admin/complaints", label: "Complaints", Icon: IconList },
  { href: "/admin/map", label: "Map", Icon: IconPin },
  { href: "/admin/overdue", label: "Overdue", Icon: IconFlag },
];

// Phone navigation: stays within thumb reach. Hidden on larger screens (the top bar takes over).
export default function BottomNav({ tabs = CITIZEN_TABS }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-white md:hidden">
      <ul className="mx-auto grid max-w-md" style={{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }}>
        {tabs.map(({ href, label, Icon, exact, primary }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-col items-center gap-0.5 py-2 text-[11px] font-semibold ${
                  active ? "text-highway" : "text-asphalt-soft"
                }`}
              >
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full ${
                    primary ? "bg-signal text-asphalt" : active ? "bg-highway-tint" : ""
                  }`}
                >
                  <Icon size={20} />
                </span>
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
