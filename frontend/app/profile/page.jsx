"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useLanguage, useT } from "@/context/LanguageContext";
import { api } from "@/lib/api";
import { LANGUAGES } from "@/lib/i18n";
import { fieldErrorsFromApi } from "@/lib/validation";
import { profileChanges, validatePasswordChange, validateProfile } from "@/lib/profile";
import { btnPrimary, plate } from "@/lib/ui";
import RoleGuard from "@/components/RoleGuard";
import BottomNav, { ADMIN_TABS, CITIZEN_TABS, WORKER_TABS } from "@/components/BottomNav";
import PageHeader from "@/components/PageHeader";
import FormField from "@/components/FormField";
import Alert from "@/components/Alert";

const TABS = { CITIZEN: CITIZEN_TABS, WORKER: WORKER_TABS, ADMIN: ADMIN_TABS };

function DetailsForm() {
  const { user, refresh } = useAuth();
  const t = useT();
  const [form, setForm] = useState({ name: user.name || "", phone: user.phone || "" });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState({ type: "success", text: "" });
  const [busy, setBusy] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setMessage({ type: "success", text: "" });
    const found = validateProfile(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    const changes = profileChanges(form, user);
    if (!Object.keys(changes).length) {
      setMessage({ type: "info", text: t("Nothing to save. You have not changed anything.") });
      return;
    }
    setBusy(true);
    try {
      await api.patch("/users/me", changes);
      await refresh();
      setMessage({ type: "success", text: t("Profile updated") });
    } catch (err) {
      setErrors(fieldErrorsFromApi(err.errors));
      setMessage({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className={`${plate} space-y-4 p-5`} aria-labelledby="details-title">
      <h2 id="details-title" className="text-lg font-bold">{t("Your details")}</h2>
      <Alert type={message.type}>{message.text}</Alert>
      <FormField id="name" label={t("Name")} autoComplete="name" value={form.name} onChange={onChange} error={errors.name && t(errors.name)} />
      <FormField id="phone" label={t("Phone (optional)")} type="tel" autoComplete="tel" value={form.phone} onChange={onChange} error={errors.phone && t(errors.phone)} hint={t("10-15 digits, e.g. +919876543210")} />
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-semibold text-asphalt-soft">{t("Email")}</dt>
          <dd className="mt-0.5 break-all font-medium">{user.email}</dd>
        </div>
        <div>
          <dt className="font-semibold text-asphalt-soft">{t("Role")}</dt>
          <dd className="mt-0.5 font-medium">{t(user.role === "CITIZEN" ? "Citizen" : user.role === "WORKER" ? "Worker" : "Admin")}</dd>
        </div>
      </dl>
      <button type="submit" disabled={busy} className={btnPrimary}>
        {busy ? t("Saving...") : t("Save changes")}
      </button>
    </form>
  );
}

function PasswordForm() {
  const t = useT();
  const empty = { currentPassword: "", newPassword: "", confirmPassword: "" };
  const [form, setForm] = useState(empty);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState({ type: "success", text: "" });
  const [busy, setBusy] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setMessage({ type: "success", text: "" });
    const found = validatePasswordChange(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      await api.post("/users/me/change-password", { currentPassword: form.currentPassword, newPassword: form.newPassword });
      setForm(empty);
      setMessage({ type: "success", text: t("Password changed") });
    } catch (err) {
      setErrors(fieldErrorsFromApi(err.errors));
      setMessage({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  const err = (k) => errors[k] && t(errors[k]);
  return (
    <form onSubmit={onSubmit} noValidate className={`${plate} space-y-4 p-5`} aria-labelledby="password-title">
      <h2 id="password-title" className="text-lg font-bold">{t("Change password")}</h2>
      <Alert type={message.type}>{message.text}</Alert>
      <FormField id="currentPassword" label={t("Current password")} type="password" autoComplete="current-password" value={form.currentPassword} onChange={onChange} error={err("currentPassword")} />
      <FormField id="newPassword" label={t("New password")} type="password" autoComplete="new-password" value={form.newPassword} onChange={onChange} error={err("newPassword")} hint={t("At least 8 characters with a letter and a number")} />
      <FormField id="confirmPassword" label={t("Confirm new password")} type="password" autoComplete="new-password" value={form.confirmPassword} onChange={onChange} error={err("confirmPassword")} />
      <button type="submit" disabled={busy} className={btnPrimary}>
        {busy ? t("Changing...") : t("Change password")}
      </button>
    </form>
  );
}

function LanguageChoice() {
  const { lang, setLang } = useLanguage();
  const t = useT();
  return (
    <section className={`${plate} p-5`} aria-labelledby="language-title">
      <h2 id="language-title" className="text-lg font-bold">{t("Language")}</h2>
      <p className="mt-1 text-sm text-asphalt-soft">{t("Choose the language of the website.")}</p>
      <div role="radiogroup" aria-label={t("Language")} className="mt-3 flex flex-wrap gap-2">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            type="button"
            role="radio"
            aria-checked={lang === l.code}
            onClick={() => setLang(l.code)}
            className={`rounded-full border px-4 py-1.5 text-sm font-semibold ${
              lang === l.code ? "border-asphalt bg-asphalt text-white" : "border-line bg-white text-asphalt hover:bg-concrete"
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>
    </section>
  );
}

function ProfileBody() {
  const { user } = useAuth();
  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <PageHeader title="My profile" />
      <DetailsForm />
      <PasswordForm />
      <LanguageChoice />
      <BottomNav tabs={TABS[user.role]} />
    </div>
  );
}

export default function ProfilePage() {
  return (
    <RoleGuard roles={["CITIZEN", "WORKER", "ADMIN"]}>
      <ProfileBody />
    </RoleGuard>
  );
}
