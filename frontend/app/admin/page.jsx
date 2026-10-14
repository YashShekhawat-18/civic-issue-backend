"use client";

import { useAuth } from "@/context/AuthContext";

export default function Page() {
  const { user } = useAuth();
  return (
    <section>
      <h1 className="text-2xl font-bold">Admin dashboard</h1>
      <p className="mt-2 text-slate-600">Hello, {user?.name}. Statistics, complaint management and settings will appear here in later phases.</p>
    </section>
  );
}
