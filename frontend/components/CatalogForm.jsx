"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { fieldErrorsFromApi } from "@/lib/validation";
import { changedFields, suggestCode, validateCatalog } from "@/lib/manage";
import FormField from "./FormField";
import SelectField from "./SelectField";
import Alert from "./Alert";
import { btnPrimary, btnSecondary, plate } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";

/**
 * Add or edit a department or a category.
 * kind: "department" | "category".  item: the record being edited (omit to add a new one).
 * departments: the department list (categories only, for the "Department" choice).
 */
export default function CatalogForm({ kind, item, departments = [], onSaved, onCancel }) {
  const t = useT();
  const editing = Boolean(item);
  const isCategory = kind === "category";
  const base = isCategory ? "/categories" : "/departments";
  const [form, setForm] = useState({
    name: item?.name ?? "",
    code: item?.code ?? "",
    description: item?.description ?? "",
    departmentId: item?.department?.id ?? "",
  });
  const [codeTouched, setCodeTouched] = useState(editing);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [busy, setBusy] = useState(false);

  function onChange(e) {
    const { name, value } = e.target;
    setForm((f) => {
      const next = { ...f, [name]: value };
      if (name === "name" && !codeTouched) next.code = suggestCode(value); // code follows the name until the admin edits it
      return next;
    });
    if (name === "code") setCodeTouched(true);
  }

  async function onSubmit(e) {
    e.preventDefault();
    setServerError("");
    const found = validateCatalog(form, { needsDepartment: isCategory });
    setErrors(found);
    if (Object.keys(found).length) return;

    const values = {
      name: form.name.trim(),
      code: form.code.trim().toUpperCase(),
      description: form.description.trim(),
      ...(isCategory ? { departmentId: form.departmentId } : {}),
    };
    setBusy(true);
    try {
      if (editing) {
        const before = { name: item.name, code: item.code, description: item.description || "", ...(isCategory ? { departmentId: item.department?.id } : {}) };
        const body = changedFields(before, values);
        if (!Object.keys(body).length) {
          setServerError("Nothing was changed.");
          setBusy(false);
          return;
        }
        await api.patch(`${base}/${item.id}`, body);
      } else {
        await api.post(base, values);
      }
      onSaved(editing ? `${values.name} updated.` : `${values.name} added.`);
    } catch (err) {
      setErrors(fieldErrorsFromApi(err.errors));
      setServerError(err.message);
      setBusy(false);
    }
  }

  const noun = isCategory ? "category" : "department";
  return (
    <form onSubmit={onSubmit} noValidate className={`${plate} mb-5 space-y-4 p-5`} aria-label={editing ? `Edit ${noun}` : `Add ${noun}`}>
      <h2 className="text-lg font-bold">{editing ? `Edit ${item.name}` : `Add a ${noun}`}</h2>
      <Alert type="error">{serverError}</Alert>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField id="name" label={t("Name")} value={form.name} onChange={onChange} error={errors.name} />
        <FormField id="code" label={t("Code")} value={form.code} onChange={onChange} error={errors.code} hint={t("Capital letters, digits and underscores. Used internally.")} />
      </div>
      {isCategory && (
        <SelectField id="departmentId" label={t("Department")} value={form.departmentId} onChange={onChange} error={errors.departmentId}>
          <option value="">{t("Select a department")}</option>
          {departments.filter((d) => d.isActive || d.id === item?.department?.id).map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </SelectField>
      )}
      <FormField id="description" label={t("Description (optional)")} value={form.description} onChange={onChange} error={errors.description} />
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={busy} className={btnPrimary}>{busy ? "Saving..." : editing ? "Save changes" : `Add ${noun}`}</button>
        <button type="button" onClick={onCancel} className={btnSecondary}>{t("Cancel")}</button>
      </div>
    </form>
  );
}
