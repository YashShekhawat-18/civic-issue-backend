"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import WorkerForm from "@/components/WorkerForm";
import InlineConfirm from "@/components/InlineConfirm";
import ActiveBadge from "@/components/ActiveBadge";
import SelectField from "@/components/SelectField";
import Pagination from "@/components/Pagination";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { btnGhost, btnPrimary, plate } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";

const LIMIT = 20;

export default function WorkersPage() {
  const t = useT();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ departmentId: "", isActive: "" });
  const depts = useApi("/admin/departments");
  const { data, error, loading, reload } = useApi("/admin/workers", { ...filters, page, limit: LIMIT });
  const [editing, setEditing] = useState(null);
  const [notice, setNotice] = useState({ type: "success", text: "" });

  const saved = (text) => { setEditing(null); setNotice({ type: "success", text }); reload(); };
  const filter = (e) => { setFilters({ ...filters, [e.target.name]: e.target.value }); setPage(1); };
  async function setActive(w, isActive) {
    setNotice({ type: "success", text: "" });
    try {
      await api.patch(`/admin/workers/${w.id}`, { isActive });
      setNotice({ type: "success", text: `${w.name} ${isActive ? "can log in again" : "can no longer log in"}.` });
      reload();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  }

  return (
    <div>
      <PageHeader title={t("Workers")}>
        {editing === null && depts.data && <button onClick={() => setEditing("new")} className={btnPrimary}>{t("Add worker")}</button>}
      </PageHeader>
      <p className="-mt-3 mb-5 text-sm text-asphalt-soft">{t("Workers fix complaints for their own department. Only an admin can create them.")}</p>
      <div className="mb-4"><Alert type={notice.type}>{notice.text}</Alert></div>
      {editing && depts.data && (
        <WorkerForm worker={editing === "new" ? undefined : editing} departments={depts.data} onSaved={saved} onCancel={() => setEditing(null)} />
      )}

      <div className="mb-4 grid grid-cols-2 gap-3 sm:max-w-md">
        <SelectField id="departmentId" label={t("Department")} value={filters.departmentId} onChange={filter}>
          <option value="">{t("All")}</option>
          {(depts.data || []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </SelectField>
        <SelectField id="isActive" label={t("Status")} value={filters.isActive} onChange={filter}>
          <option value="">{t("All")}</option>
          <option value="true">{t("Active")}</option>
          <option value="false">{t("Inactive")}</option>
        </SelectField>
      </div>

      {loading && !data ? <Spinner /> : error && !data ? <Alert type="error">{error}</Alert> : !data.items.length ? (
        <EmptyState title={t("No workers found")} text={t("Add a worker, then assign complaints from the complaint page.")} />
      ) : (
        <div className={loading ? "opacity-60" : ""}>
          <ul className="space-y-3">
            {data.items.map((w) => (
              <li key={w.id} className={`${plate} flex flex-wrap items-center justify-between gap-3 p-4`}>
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 font-bold">{w.name} <ActiveBadge active={w.isActive} /></p>
                  <p className="break-all text-sm text-asphalt-soft">{w.email}{w.phone ? ` - ${w.phone}` : ""}</p>
                  <p className="text-sm text-asphalt-soft">{w.department?.name ?? "No department"}</p>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  <button className={btnGhost} onClick={() => setEditing(w)} aria-label={`Edit ${w.name}`}>{t("Edit")}</button>
                  {w.isActive ? (
                    <InlineConfirm label={t("Deactivate")} confirmLabel={`Yes, deactivate ${w.name}`} onConfirm={() => setActive(w, false)} />
                  ) : (
                    <button className={btnGhost} onClick={() => setActive(w, true)}>{t("Reactivate")}</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <Pagination page={page} limit={LIMIT} total={data.total} onChange={setPage} />
        </div>
      )}
    </div>
  );
}
