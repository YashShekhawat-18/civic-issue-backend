"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { homeFor } from "@/lib/roles";
import Spinner from "./Spinner";

// For /login and /register: a logged-in user is sent to their own home instead.
export default function GuestOnly({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace(homeFor(user.role));
  }, [loading, user, router]);

  if (loading || user) return <Spinner />;
  return children;
}
