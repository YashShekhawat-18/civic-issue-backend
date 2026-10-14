"use client";

import { useAuth } from "@/context/AuthContext";

export default function Page() {
  const { user } = useAuth();
  return (
    <section>
      <h1 className="text-2xl font-bold">Citizen home</h1>
      <p className="mt-2 text-slate-600">Hello, {user?.name}. Reporting, your complaints, nearby issues and points will appear here in the next phases.</p>
    </section>
  );
}
