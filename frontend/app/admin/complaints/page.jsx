"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import { STATUS_INFO, STATUS_ORDER } from "@/lib/status";
import TaskCard from "@/components/TaskCard";
import Pagination from "@/components/Pagination";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { btnGhost } from "@/lib/ui";

const LIMIT = 20;
const EMPTY = { status: "", departmentId: "", categoryId: "", overdue: false, number: "" };
const field = "w-full rounded-lg border border-line bg-white px-3 py-2 text-sm";

// Remounted (key = the filters) whenever a filter changes, so it always starts on page 1.
function Results({ filters }) {
  const [page, setPage] = useState(1);
  const { data, error, loading } = useApi("/admin/complaints", {
    status: filters.status,
    departmentId: filters.departmentId,
    categoryId: filters.categoryId,
    overdue: filters.overdue ? "true" : "",
    number: filters.number,
    page,
    limit: LIMIT,
  });

  if (loading && !data) return <Spinner />;
  if (error && !data) return <Alert type="error">{error}</Alert>;
  if (!data.items.length)
    return <EmptyState title="No complaints match these filters" text="Clear a filter or search for another number." />;

  return (
    <div className={loading ? "opacity-60" : ""}>
      <p className="mb-3 text-sm text-asphalt-soft" data-testid="result-count">
        {data.total} {data.total === 1 ? "complaint" : "complaints"}
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
  );
}

function Complaints() {
  const params = useSearchParams();
  const initial = { ...EMPTY, status: STATUS_ORDER.includes(params.get("status")) ? params.get("status") : "", overdue: params.get("overdue") === "true" };
  const [filters, setFilters] = useState(initial);
  const [numberInput, setNumberInput] = useState("");
  const departments = useApi("/admin/departments");
  const categories = useApi("/admin/categories");
  const set = (name) => (e) => setFilters({ ...filters, [name]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const active = JSON.stringify(filters) !== JSON.stringify(EMPTY);

  return (
    <div>
      <PageHeader title="Complaints" />

      <form
        aria-label="Filters"
        onSubmit={(e) => {
          e.preventDefault();
          setFilters({ ...filters, number: numberInput.trim() });
        }}
        className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
      >
        <label className="text-sm font-semibold">
          Progress
          <select className={`${field} mt-1 font-normal`} value={filters.status} onChange={set("status")}>
            <option value="">All</option>
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {STATUS_INFO[s].label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold">
          Department
          <select className={`${field} mt-1 font-normal`} value={filters.departmentId} onChange={set("departmentId")}>
            <option value="">All</option>
            {(departments.data || []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold">
          Category
          <select className={`${field} mt-1 font-normal`} value={filters.categoryId} onChange={set("categoryId")}>
            <option value="">All</option>
            {(categories.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold">
          Complaint number
          <span className="mt-1 flex gap-2">
            <input
              className={`${field} font-normal`}
              placeholder="CIV-2026-000001"
              value={numberInput}
              onChange={(e) => setNumberInput(e.target.value)}
            />
            <button type="submit" className="rounded-lg bg-asphalt px-3 text-sm font-semibold text-white">
              Find
            </button>
          </span>
        </label>
        <label className="flex items-center gap-2 text-sm font-semibold">
          <input type="checkbox" checked={filters.overdue} onChange={set("overdue")} />
          Only overdue
        </label>
        {active && (
          <button
            type="button"
            className={`${btnGhost} justify-self-start`}
            onClick={() => {
              setFilters(EMPTY);
              setNumberInput("");
            }}
          >
            Clear filters
          </button>
        )}
      </form>

      <Results key={JSON.stringify(filters)} filters={filters} />
    </div>
  );
}

export default function AdminComplaintsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <Complaints />
    </Suspense>
  );
}
