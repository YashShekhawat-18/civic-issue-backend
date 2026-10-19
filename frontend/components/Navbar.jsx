"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ROLE_MENU, homeFor } from "@/lib/roles";
import { IconBell, IconLogout, IconStar, IconUser } from "./icons";
import LanguageSwitch from "./LanguageSwitch";
import { useT } from "@/context/LanguageContext";
import { useApi } from "@/hooks/useApi";
import { useEffect, useState } from "react";
import { NOTIFICATIONS_CHANGED } from "@/lib/events";

function NotificationBell() {
  const pathname = usePathname();
  const [changes, setChanges] = useState(0);
  // Re-check when the citizen moves to another page, or when alerts are marked as read.
  useEffect(() => {
    const onChange = () => setChanges((n) => n + 1);
    window.addEventListener(NOTIFICATIONS_CHANGED, onChange);
    return () => window.removeEventListener(NOTIFICATIONS_CHANGED, onChange);
  }, []);
  const { data } = useApi("/notifications", { limit: 1 }, `${pathname}|${changes}`);
  const unread = data?.unreadCount ?? 0;
  return (
    <Link
      href="/citizen/notifications"
      aria-label={unread ? `Alerts, ${unread} unread` : "Alerts"}
      className="relative rounded-lg p-2 text-white/90 hover:bg-white/10"
    >
      <IconBell size={22} />
      {unread > 0 && (
        <span
          data-testid="unread-count"
          className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-signal px-1 text-[11px] font-bold text-asphalt"
        >
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}

export default function Navbar() {
  const t = useT();
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  const menu = user ? ROLE_MENU[user.role] || [] : [];
  const isCitizen = user?.role === "CITIZEN";

  return (
    <header className="sticky top-0 z-30 bg-asphalt text-white">
      {/* a thin road marking along the top edge */}
      <div
        aria-hidden="true"
        className="h-1"
        style={{ backgroundImage: "repeating-linear-gradient(90deg,#f6b400 0 18px,transparent 18px 30px)" }}
      />
      <nav className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-2.5">
        <Link href={user ? homeFor(user.role) : "/"} className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-signal font-display text-lg font-extrabold text-asphalt">
            C
          </span>
          <span className={`hidden whitespace-nowrap font-display text-lg font-bold ${isCitizen ? "xl:inline" : "sm:inline"}`}>{t("Civic Issue Reporter")}</span>
        </Link>

        {/* desktop menu; on phones citizens get the bottom bar instead */}
        <ul className={`ml-4 items-center gap-1 ${isCitizen ? "hidden md:flex" : "hidden sm:flex"}`}>
          {menu.map((item) => {
            const active = item.match ? pathname.startsWith(item.match) : pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`whitespace-nowrap rounded-lg px-2.5 py-1.5 text-sm font-medium ${
                    active ? "bg-white/15 text-white" : "text-white/75 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {t(item.label)}
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="ml-auto flex items-center gap-1.5 text-sm">
          <LanguageSwitch />
          {loading ? null : user ? (
            <>
              {isCitizen && (
                <>
                  <Link
                    href="/citizen/rewards"
                    aria-label={`${user.points ?? 0} points. Open rewards`}
                    className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 font-semibold hover:bg-white/20"
                  >
                    <IconStar size={15} className="text-signal" />
                    <span data-testid="points">{user.points ?? 0}</span>
                  </Link>
                  <NotificationBell />
                </>
              )}
              {!isCitizen && (
                <span className="hidden text-white/80 lg:inline">
                  {user.name} <span className="rounded bg-white/15 px-1.5 py-0.5 text-xs">{user.role}</span>
                </span>
              )}
              <Link
                href="/profile"
                aria-label={t("Profile")}
                aria-current={pathname === "/profile" ? "page" : undefined}
                className="rounded-lg p-2 text-white/90 hover:bg-white/10"
              >
                <IconUser size={20} />
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 whitespace-nowrap rounded-lg px-2.5 py-2 text-white/85 hover:bg-white/10"
                aria-label={t("Log out")}
              >
                <IconLogout size={18} />
                <span className="hidden sm:inline">{t("Log out")}</span>
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="rounded-lg px-3 py-1.5 font-medium hover:bg-white/10">
                {t("Log in")}
              </Link>
              <Link href="/register" className="rounded-lg bg-signal px-3.5 py-1.5 font-semibold text-asphalt hover:brightness-95">
                {t("Register")}
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
