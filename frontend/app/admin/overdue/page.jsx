"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import TaskCard from "@/components/TaskCard";
import Pagination from "@/components/Pagination";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { btnSecondary } from "@/lib/ui";

const LIMIT = 20;

export default function OverduePage() {
  const [page, setPage] = useState(1);
  const { data, error, loading, reload } = useApi("/admin/overdue", { page, limit: LIMIT });
  const [check, setCheck] = useState({ busy: false, message: "", error: "" });

  async function runCheck() {
    setCheck({ busy: true, message: "", error: "" });
    try {
      const r = await api.post("/admin/overdue/check");
      setCheck({ busy: false, error: "", message: `Checked ${r.checked} open complaints. ${r.markedOverdue} newly marked overdue.` });
      reload();
    } catch (err) {
      setCheck({ busy: false, message: "", error: err.message });
    }
  }

  return (
    <div>
      <PageHeader title="Overdue complaints">
        <button onClick={runCheck} disabled={check.busy} className={btnSecondary}>
          {check.busy ? "Checking..." : "Run overdue check now"}
        </button>
      </PageHeader>
      <p className="-mt-3 mb-5 text-sm text-asphalt-soft">Open complaints that have waited too long, oldest first. The check also runs by itself every hour.</p>

      <div className="mb-4 space-y-3">
        <Alert type="success">{check.message}</Alert>
        <Alert type="error">{check.error}</Alert>
      </div>

      {loading && !data ? (
        <Spinner />
      ) : error && !data ? (
        <Alert type="error">{error}</Alert>
      ) : !data.items.length ? (
        <EmptyState title="Nothing is overdue" text="Every open complaint is within the time limit." />
      ) : (
        <div className={loading ? "opacity-60" : ""}>
          <p className="mb-3 text-sm text-asphalt-soft" data-testid="overdue-count">
            {data.total} overdue
          </p>
          <ul className="space-y-3">
            {data.items.map((c) => (
              <li key={c.id}>
                <TaskCard task={c} base="/admin/complaints" showDepartment />
              </li>
            ))}
          </ul>
          <Pagination page={page} limit={LIMIT} total={data.total} onChange={setPage} />
        </div>
      )}
    </div>
  );
}
