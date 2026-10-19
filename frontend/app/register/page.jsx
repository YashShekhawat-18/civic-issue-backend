"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { fieldErrorsFromApi, validateRegister } from "@/lib/validation";
import FormField from "@/components/FormField";
import Alert from "@/components/Alert";
import GuestOnly from "@/components/GuestOnly";
import AuthShell from "@/components/AuthShell";
import { useT } from "@/context/LanguageContext";
import { btnPrimary } from "@/lib/ui";

const EMPTY = { name: "", email: "", phone: "", password: "", confirmPassword: "" };

function RegisterForm() {
  const { register } = useAuth();
  const t = useT();
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setServerError("");
    const found = validateRegister(form);
    setErrors(found);
    if (Object.keys(found).length) return;

    setSubmitting(true);
    try {
      await register(form);
      router.replace("/login?registered=1");
    } catch (err) {
      setErrors(fieldErrorsFromApi(err.errors));
      setServerError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <h1 className="mb-1 text-3xl font-extrabold">{t("Create your account")}</h1>
      <p className="mb-6 text-asphalt-soft">{t("Free for citizens. Staff accounts are created by an admin.")}</p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Alert type="error">{serverError}</Alert>
        <FormField id="name" label={t("Full name")} autoComplete="name" value={form.name} onChange={onChange} error={errors.name} />
        <FormField id="email" label={t("Email")} type="email" autoComplete="email" value={form.email} onChange={onChange} error={errors.email} />
        <FormField id="phone" label={t("Phone (optional)")} type="tel" autoComplete="tel" value={form.phone} onChange={onChange} error={errors.phone} hint={t("10-15 digits, e.g. +919876543210")} />
        <FormField id="password" label={t("Password")} type="password" autoComplete="new-password" value={form.password} onChange={onChange} error={errors.password} hint={t("At least 8 characters with a letter and a number")} />
        <FormField id="confirmPassword" label={t("Confirm password")} type="password" autoComplete="new-password" value={form.confirmPassword} onChange={onChange} error={errors.confirmPassword} />
        <button
          type="submit"
          disabled={submitting}
          className={`${btnPrimary} w-full !py-3 !text-base`}
        >
          {submitting ? t("Creating account...") : t("Register")}
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-asphalt-soft">
        {t("Already registered?")}{" "}
        <Link href="/login" className="font-semibold text-sign hover:underline">
          {t("Log in")}
        </Link>
      </p>
    </AuthShell>
  );
}

export default function RegisterPage() {
  return (
    <GuestOnly>
      <RegisterForm />
    </GuestOnly>
  );
}
