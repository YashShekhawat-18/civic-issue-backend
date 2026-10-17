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

export default function CategoriesPage() {
  const cats = useApi("/admin/categories");
  const depts = useApi("/admin/departments");
  const [editing, setEditing] = useState(null);
  const [notice, setNotice] = useState({ type: "success", text: "" });

  const saved = (text) => { setEditing(null); setNotice({ type: "success", text }); cats.reload(); };
  async function setActive(c, isActive) {
    setNotice({ type: "success", text: "" });
    try {
      await api.patch(`/categories/${c.id}`, { isActive });
      setNotice({ type: "success", text: `${c.name} ${isActive ? "reactivated" : "deactivated"}.` });
      cats.reload();
    } catch (err) {
      setNotice({ type: "error", text: err.message });
    }
  }
  const data = cats.data;

  return (
    <div>
      <PageHeader title="Categories">
        {editing === null && depts.data && <button onClick={() => setEditing("new")} className={btnPrimary}>Add category</button>}
      </PageHeader>
      <p className="-mt-3 mb-5 text-sm text-asphalt-soft">A category decides which department receives a complaint.</p>
      <div className="mb-4"><Alert type={notice.type}>{notice.text}</Alert></div>
      {editing && depts.data && (
        <CatalogForm kind="category" item={editing === "new" ? undefined : editing} departments={depts.data} onSaved={saved} onCancel={() => setEditing(null)} />
      )}
      {cats.loading && !data ? <Spinner /> : cats.error && !data ? <Alert type="error">{cats.error}</Alert> : !data.length ? (
        <EmptyState title="No categories yet" text="Add a category and choose the department that handles it." />
      ) : (
        <ul className="space-y-3">
          {data.map((c) => (
            <li key={c.id} className={`${plate} flex flex-wrap items-center justify-between gap-3 p-4`}>
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 font-bold">{c.name} <ActiveBadge active={c.isActive} /></p>
                <p className="text-sm text-asphalt-soft">Goes to {c.department?.name ?? "no department"} - {c.code}</p>
              </div>
              <div className="flex flex-wrap items-center gap-1">
                <button className={btnGhost} onClick={() => setEditing(c)} aria-label={`Edit ${c.name}`}>Edit</button>
                {c.isActive ? (
                  <InlineConfirm label="Deactivate" confirmLabel={`Yes, deactivate ${c.name}`} onConfirm={() => setActive(c, false)} />
                ) : (
                  <button className={btnGhost} onClick={() => setActive(c, true)}>Reactivate</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
