"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import CatalogForm from "@/components/CatalogForm";
import InlineConfirm from "@/components/InlineConfirm";
import ActiveBadge from "@/components/ActiveBadge";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { btnGhost, btnPrimary, plate } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";

export default function DepartmentsPage() {
  const t = useT();
  const { data, error, loading, reload } = useApi("/admin/departments");
  const [editing, setEditing] = useState(null); // null | "new" | a department
  const [notice, setNotice] = useState({ type: "success", text: "" });

  const saved = (text) => { setEditing(null); setNotice({ type: "success", text }); reload(); };
  async function setActive(d, isActive) {
    setNotice({ type: "success", text: "" });
    try {
      await api.patch(`/departments/${d.id}`, { isActive });
      setNotice({ type: "success", text: `${d.name} ${isActive ? "reactivated" : "deactivated"}.` });
      reload();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  }

  return (
    <div>
      <PageHeader title={t("Departments")}>
        {editing === null && <button onClick={() => setEditing("new")} className={btnPrimary}>{t("Add department")}</button>}
      </PageHeader>
      <div className="mb-4"><Alert type={notice.type}>{notice.text}</Alert></div>
      {editing && (
        <CatalogForm kind="department" item={editing === "new" ? undefined : editing} onSaved={saved} onCancel={() => setEditing(null)} />
      )}
      {loading && !data ? <Spinner /> : error && !data ? <Alert type="error">{error}</Alert> : !data.length ? (
        <EmptyState title={t("No departments yet")} text={t("Add the first department. Categories and workers belong to one.")} />
      ) : (
        <ul className="space-y-3">
          {data.map((d) => (
            <li key={d.id} className={`${plate} flex flex-wrap items-center justify-between gap-3 p-4`}>
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 font-bold">{d.name} <ActiveBadge active={d.isActive} /></p>
                <p className="text-sm text-asphalt-soft">{d.code}{d.description ? ` - ${d.description}` : ""}</p>
              </div>
              <div className="flex flex-wrap items-center gap-1">
                <button className={btnGhost} onClick={() => setEditing(d)} aria-label={`Edit ${d.name}`}>{t("Edit")}</button>
                {d.isActive ? (
                  <InlineConfirm label={t("Deactivate")} confirmLabel={`Yes, deactivate ${d.name}`} onConfirm={() => setActive(d, false)} />
                ) : (
                  <button className={btnGhost} onClick={() => setActive(d, true)}>{t("Reactivate")}</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
