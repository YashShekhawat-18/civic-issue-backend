"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export default function Page() {
  const { user } = useAuth();
  return (
    <section>
      <h1 className="text-2xl font-bold">Citizen home</h1>
      <p className="mt-2 text-slate-600">Hello, {user?.name}. See something broken in your area?</p>
      <Link
        href="/citizen/report"
        className="mt-5 inline-block rounded-md bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700"
      >
        Report an issue
      </Link>
      <p className="mt-6 text-sm text-slate-500">Your complaints, nearby issues and points will appear here in the next phase.</p>
    </section>
  );
}
