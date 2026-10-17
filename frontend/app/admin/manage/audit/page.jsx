"use client";

import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { AUDIT_ACTIONS, AUDIT_ENTITIES, describeAudit } from "@/lib/manage";
import { formatDateTime } from "@/lib/format";
import SelectField from "@/components/SelectField";
import Pagination from "@/components/Pagination";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { plate } from "@/lib/ui";

const LIMIT = 20;

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ action: "", entity: "" });
  const { data, error, loading } = useApi("/admin/audit-logs", { ...filters, page, limit: LIMIT });
  const filter = (e) => { setFilters({ ...filters, [e.target.name]: e.target.value }); setPage(1); };

  return (
    <div>
      <PageHeader title="Activity log" />
      <p className="-mt-3 mb-5 text-sm text-asphalt-soft">Who did what, newest first. Entries cannot be edited or deleted.</p>
      <div className="mb-4 grid grid-cols-1 gap-3 sm:max-w-xl sm:grid-cols-2">
        <SelectField id="action" label="What happened" value={filters.action} onChange={filter}>
          <option value="">Everything</option>
          {AUDIT_ACTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </SelectField>
        <SelectField id="entity" label="About" value={filters.entity} onChange={filter}>
          <option value="">Everything</option>
          {AUDIT_ENTITIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </SelectField>
      </div>

      {loading && !data ? <Spinner /> : error && !data ? <Alert type="error">{error}</Alert> : !data.items.length ? (
        <EmptyState title="Nothing logged yet" text="Changes made by admins, workers and citizens show up here." />
      ) : (
        <div className={loading ? "opacity-60" : ""}>
          <p className="mb-3 text-sm text-asphalt-soft" data-testid="audit-count">{data.total} {data.total === 1 ? "entry" : "entries"}</p>
          <ul className="space-y-2">
            {data.items.map((entry) => {
              const { title, detail } = describeAudit(entry);
              return (
                <li key={entry.id} className={`${plate} p-4`} data-testid="audit-entry">
                  <p className="font-semibold">{title}</p>
                  {detail && <p className="text-sm text-asphalt-soft">{detail}</p>}
                  <p className="mt-1 text-xs text-asphalt-soft">
                    {entry.user ? `${entry.user.name} (${entry.user.role.toLowerCase()})` : "Unknown user"} - {formatDateTime(entry.createdAt)}
                  </p>
                </li>
              );
            })}
          </ul>
          <Pagination page={page} limit={LIMIT} total={data.total} onChange={setPage} />
        </div>
      )}
    </div>
  );
}
