"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import TaskCard from "@/components/TaskCard";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { FILTERS } from "@/lib/tasks";
import { btnSecondary } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";

const PAGE_SIZE = 10;

// Remounted (key=filter) whenever the filter changes, so it starts at page 1.
function TaskList({ filter }) {
  const t = useT();
  const first = useApi("/worker/complaints", { ...filter.query, page: 1, limit: PAGE_SIZE });
  const [extra, setExtra] = useState([]);
  const [nextPage, setNextPage] = useState(2);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState("");

  async function showMore() {
    setLoadingMore(true);
    setMoreError("");
    try {
      const data = await api.get("/worker/complaints", { ...filter.query, page: nextPage, limit: PAGE_SIZE });
      setExtra((prev) => [...prev, ...data.items]);
      setNextPage(nextPage + 1);
    } catch (err) {
      setMoreError(err.message);
    } finally {
      setLoadingMore(false);
    }
  }

  if (first.loading) return <Spinner />;
  if (first.error) return <Alert type="error">{first.error}</Alert>;

  const items = [...first.data.items, ...extra];
  const total = first.data.total;
  if (!items.length) return <EmptyState title={filter.empty} text={t("Try another filter to see other complaints.")} />;

  return (
    <>
      <ul className="space-y-3">
        {items.map((task) => (
          <li key={task.id}>
            <TaskCard task={task} />
          </li>
        ))}
      </ul>
      <div className="mt-5 space-y-3 text-center">
        <Alert type="error">{moreError}</Alert>
        <p className="text-sm text-asphalt-soft">
          Showing {items.length} of {total}
        </p>
        {items.length < total && (
          <button onClick={showMore} disabled={loadingMore} className={btnSecondary}>
            {loadingMore ? "Loading..." : "Show more"}
          </button>
        )}
      </div>
    </>
  );
}

function Tasks() {
  const t = useT();
  const requested = useSearchParams().get("filter");
  const [key, setKey] = useState(FILTERS.some((f) => f.key === requested) ? requested : "new");
  const filter = FILTERS.find((f) => f.key === key);

  return (
    <div>
      <PageHeader title={t("Tasks")} />
      <div role="group" aria-label={t("Filter tasks")} className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setKey(f.key)}
            aria-pressed={key === f.key}
            className={`rounded-full border px-4 py-1.5 text-sm font-semibold ${
              key === f.key ? "border-asphalt bg-asphalt text-white" : "border-line bg-white text-asphalt hover:bg-concrete"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
      <TaskList key={key} filter={filter} />
    </div>
  );
}

export default function TasksPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <Tasks />
    </Suspense>
  );
}
