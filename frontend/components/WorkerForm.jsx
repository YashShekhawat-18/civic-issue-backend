"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { fieldErrorsFromApi } from "@/lib/validation";
import { changedFields, validateWorker } from "@/lib/manage";
import FormField from "./FormField";
import SelectField from "./SelectField";
import Alert from "./Alert";
import { btnPrimary, btnSecondary, plate } from "@/lib/ui";

// Add a worker (email + password), or edit one (move department, reset password).
export default function WorkerForm({ worker, departments, onSaved, onCancel }) {
  const editing = Boolean(worker);
  const [form, setForm] = useState({
    name: worker?.name ?? "",
    email: worker?.email ?? "",
    password: "",
    phone: worker?.phone ?? "",
    departmentId: worker?.departmentId ?? "",
  });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [busy, setBusy] = useState(false);
  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setServerError("");
    const found = validateWorker(form, { creating: !editing });
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      if (editing) {
        const before = { name: worker.name, phone: worker.phone ?? "", departmentId: worker.departmentId };
        const body = changedFields(before, { name: form.name.trim(), phone: form.phone.trim(), departmentId: form.departmentId });
        if ("phone" in body) body.phone = body.phone || null; // an empty box removes the number
        if (form.password) body.password = form.password;
        if (!Object.keys(body).length) {
          setServerError("Nothing was changed.");
          setBusy(false);
          return;
        }
        await api.patch(`/admin/workers/${worker.id}`, body);
        onSaved(form.password ? `${form.name.trim()} updated and password reset.` : `${form.name.trim()} updated.`);
      } else {
        await api.post("/admin/workers", {
          name: form.name.trim(), email: form.email.trim(), password: form.password,
          departmentId: form.departmentId, ...(form.phone.trim() ? { phone: form.phone.trim() } : {}),
        });
        onSaved(`${form.name.trim()} can now log in on the Worker tab.`);
      }
    } catch (err) {
      setErrors(fieldErrorsFromApi(err.errors));
      setServerError(err.message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className={`${plate} mb-5 space-y-4 p-5`} aria-label={editing ? "Edit worker" : "Add worker"}>
      <h2 className="text-lg font-bold">{editing ? `Edit ${worker.name}` : "Add a worker"}</h2>
      <Alert type="error">{serverError}</Alert>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField id="name" label="Name" value={form.name} onChange={onChange} error={errors.name} autoComplete="off" />
        {editing ? (
          <div>
            <p className="mb-1.5 text-sm font-semibold">Email</p>
            <p className="rounded-lg bg-concrete px-3.5 py-2.5 text-asphalt-soft">{worker.email}</p>
          </div>
        ) : (
          <FormField id="email" label="Email" type="email" value={form.email} onChange={onChange} error={errors.email} autoComplete="off" />
        )}
        <FormField id="phone" label="Phone (optional)" value={form.phone} onChange={onChange} error={errors.phone} inputMode="tel" />
        <SelectField id="departmentId" label="Department" value={form.departmentId} onChange={onChange} error={errors.departmentId}>
          <option value="">Select a department</option>
          {departments.filter((d) => d.isActive || d.id === worker?.departmentId).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </SelectField>
      </div>
      <FormField
        id="password"
        label={editing ? "New password (leave empty to keep the old one)" : "Password"}
        type="password"
        value={form.password}
        onChange={onChange}
        error={errors.password}
        autoComplete="new-password"
        hint="At least 8 characters with a letter and a number. Tell the worker, they can use it to log in."
      />
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={busy} className={btnPrimary}>{busy ? "Saving..." : editing ? "Save changes" : "Add worker"}</button>
        <button type="button" onClick={onCancel} className={btnSecondary}>Cancel</button>
      </div>
    </form>
  );
}
