"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { homeFor } from "@/lib/roles";
import Spinner from "@/components/Spinner";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace(homeFor(user.role));
  }, [loading, user, router]);

  if (loading || user) return <Spinner />;

  return (
    <section className="mx-auto max-w-2xl py-16 text-center">
      <h1 className="text-4xl font-bold text-slate-900">Report civic issues. Track them to resolution.</h1>
      <p className="mt-4 text-slate-600">
        Potholes, garbage, broken streetlights, water leaks: report them with a photo and location, and follow the
        progress until they are fixed.
      </p>
      <div className="mt-8 flex justify-center gap-4">
        <Link href="/register" className="rounded-md bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700">
          Create an account
        </Link>
        <Link href="/login" className="rounded-md border border-slate-300 px-5 py-2.5 font-medium hover:bg-white">
          Log in
        </Link>
      </div>
    </section>
  );
}
