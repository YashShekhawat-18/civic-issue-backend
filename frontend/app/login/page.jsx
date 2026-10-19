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
import AuthShell from "@/components/AuthShell";
import { useT } from "@/context/LanguageContext";
import { btnPrimary } from "@/lib/ui";

// Only allow same-site relative redirects (blocks open-redirect tricks like ?next=//evil.com).
function safeNext(next) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : null;
}

const ROLE_TABS = [
  { key: "citizen", label: "Citizen", title: "Log in", hint: "Welcome back. Enter your details to continue." },
  { key: "worker", label: "Worker", title: "Worker log in", hint: "Use the email and password your admin gave you.", note: "Worker accounts are created by an admin." },
  { key: "admin", label: "Admin", title: "Admin log in", hint: "Use your administrator email and password.", note: "Admin accounts are set up by the system owner." },
];

function LoginForm() {
  const { login } = useAuth();
  const t = useT();
  const router = useRouter();
  const params = useSearchParams();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const justRegistered = params.get("registered") === "1";
  const asParam = params.get("as");
  const who = ROLE_TABS.some((rt) => rt.key === asParam) ? asParam : "citizen";
  const tab = ROLE_TABS.find((rt) => rt.key === who);

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
    <AuthShell>
      <nav aria-label="Choose how you log in" className="mb-5 grid grid-cols-3 gap-1 rounded-xl bg-concrete p-1">
        {ROLE_TABS.map((rt) => (
          <Link
            key={rt.key}
            href={rt.key === "citizen" ? "/login" : `/login?as=${rt.key}`}
            aria-current={rt.key === who ? "page" : undefined}
            className={`rounded-lg px-2 py-2 text-center text-sm font-semibold ${rt.key === who ? "bg-white shadow-sm" : "text-asphalt-soft hover:text-asphalt"}`}
          >
            {t(rt.label)}
          </Link>
        ))}
      </nav>
      <h1 className="mb-1 text-3xl font-extrabold">{t(tab.title)}</h1>
      <p className="mb-6 text-asphalt-soft">{t(tab.hint)}</p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {justRegistered && <Alert type="success">{t("Account created. Please log in.")}</Alert>}
        <Alert type="error">{serverError}</Alert>
        <FormField id="email" label={t("Email")} type="email" autoComplete="email" value={form.email} onChange={onChange} error={errors.email} />
        <FormField id="password" label={t("Password")} type="password" autoComplete="current-password" value={form.password} onChange={onChange} error={errors.password} />
        <button
          type="submit"
          disabled={submitting}
          className={`${btnPrimary} w-full !py-3 !text-base`}
        >
          {submitting ? t("Logging in...") : t("Log in")}
        </button>
      </form>
      {who === "citizen" ? (
        <p className="mt-5 text-center text-sm text-asphalt-soft">
          {t("New here?")}{" "}
          <Link href="/register" className="font-semibold text-sign hover:underline">
            {t("Create an account")}
          </Link>
        </p>
      ) : (
        <p className="mt-5 text-center text-sm text-asphalt-soft">{t(tab.note)}</p>
      )}
    </AuthShell>
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
