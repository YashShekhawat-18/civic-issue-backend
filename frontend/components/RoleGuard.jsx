"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { homeFor } from "@/lib/roles";
import Spinner from "./Spinner";

/**
 * Wrap a section so only the listed roles can see it.
 *  - not logged in  -> /login
 *  - wrong role     -> that user's own home page
 * NOTE for the viva: this only improves the UX. Real protection is the backend, which
 * checks the role on every API call. Hiding a page never secures data by itself.
 */
export default function RoleGuard({ roles, children }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const allowed = !!user && roles.includes(user.role);

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (!allowed) router.replace(homeFor(user.role));
  }, [loading, user, allowed, router, pathname]);

  if (loading || !allowed) return <Spinner />;
  return children;
}
