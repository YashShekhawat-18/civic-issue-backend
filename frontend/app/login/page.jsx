"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { homeFor } from "@/lib/roles";
import { validateLogin } from "@/lib/validation";
import FormField from "@/components/FormField";
import Alert from "@/components/Alert";
import GuestOnly from "@/components/GuestOnly";

// Only allow same-site relative redirects (blocks open-redirect tricks like ?next=//evil.com).
function safeNext(next) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : null;
}

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const justRegistered = params.get("registered") === "1";

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setServerError("");
    const found = validateLogin(form);
    setErrors(found);
    if (Object.keys(found).length) return;

    setSubmitting(true);
    try {
      const user = await login(form.email, form.password);
      const next = safeNext(params.get("next"));
      // Use the ?next target only if it belongs to this user's role area.
      const home = homeFor(user.role);
      router.replace(next && next.startsWith(home) ? next : home);
    } catch (err) {
      setServerError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="mb-1 text-2xl font-bold">Log in</h1>
      <p className="mb-5 text-sm text-slate-600">Welcome back. Enter your details to continue.</p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {justRegistered && <Alert type="success">Account created. Please log in.</Alert>}
        <Alert type="error">{serverError}</Alert>
        <FormField id="email" label="Email" type="email" autoComplete="email" value={form.email} onChange={onChange} error={errors.email} />
        <FormField id="password" label="Password" type="password" autoComplete="current-password" value={form.password} onChange={onChange} error={errors.password} />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-blue-600 py-2.5 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        New here?{" "}
        <Link href="/register" className="font-medium text-blue-700 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <GuestOnly>
      <Suspense>
        <LoginForm />
      </Suspense>
    </GuestOnly>
  );
}
