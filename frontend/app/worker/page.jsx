"use client";

import { useAuth } from "@/context/AuthContext";

export default function Page() {
  const { user } = useAuth();
  return (
    <section>
      <h1 className="text-2xl font-bold">Worker home</h1>
      <p className="mt-2 text-slate-600">Hello, {user?.name}. Your assigned tasks will appear here in a later phase.</p>
    </section>
  );
}
