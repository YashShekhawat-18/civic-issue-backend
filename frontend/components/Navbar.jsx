"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ROLE_MENU, homeFor } from "@/lib/roles";

export default function Navbar() {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  const menu = user ? ROLE_MENU[user.role] || [] : [];

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
        <Link href={user ? homeFor(user.role) : "/"} className="text-lg font-bold text-blue-700">
          Civic Issue Reporter
        </Link>
        <ul className="flex flex-1 flex-wrap items-center gap-1">
          {menu.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`rounded px-3 py-1.5 text-sm ${
                  pathname === item.href ? "bg-blue-50 font-medium text-blue-700" : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-3 text-sm">
          {loading ? null : user ? (
            <>
              <span className="text-slate-600">
                {user.name} <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{user.role}</span>
              </span>
              <button onClick={handleLogout} className="rounded border border-slate-300 px-3 py-1.5 hover:bg-slate-100">
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="rounded px-3 py-1.5 hover:bg-slate-100">
                Log in
              </Link>
              <Link href="/register" className="rounded bg-blue-600 px-3 py-1.5 text-white hover:bg-blue-700">
                Register
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
