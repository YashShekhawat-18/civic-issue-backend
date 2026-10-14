"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { fieldErrorsFromApi, validateRegister } from "@/lib/validation";
import FormField from "@/components/FormField";
import Alert from "@/components/Alert";
import GuestOnly from "@/components/GuestOnly";

const EMPTY = { name: "", email: "", phone: "", password: "", confirmPassword: "" };

function RegisterForm() {
  const { register } = useAuth();
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
    <div className="mx-auto max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="mb-1 text-2xl font-bold">Create your account</h1>
      <p className="mb-5 text-sm text-slate-600">Citizens can report and track issues. Staff accounts are created by an admin.</p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Alert type="error">{serverError}</Alert>
        <FormField id="name" label="Full name" autoComplete="name" value={form.name} onChange={onChange} error={errors.name} />
        <FormField id="email" label="Email" type="email" autoComplete="email" value={form.email} onChange={onChange} error={errors.email} />
        <FormField id="phone" label="Phone (optional)" type="tel" autoComplete="tel" value={form.phone} onChange={onChange} error={errors.phone} hint="10-15 digits, e.g. +919876543210" />
        <FormField id="password" label="Password" type="password" autoComplete="new-password" value={form.password} onChange={onChange} error={errors.password} hint="At least 8 characters with a letter and a number" />
        <FormField id="confirmPassword" label="Confirm password" type="password" autoComplete="new-password" value={form.confirmPassword} onChange={onChange} error={errors.confirmPassword} />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-blue-600 py-2.5 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting ? "Creating account..." : "Register"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-blue-700 hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <GuestOnly>
      <RegisterForm />
    </GuestOnly>
  );
}
