"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { STATUS_INFO, STATUS_ORDER } from "@/lib/status";
import ComplaintCard from "@/components/ComplaintCard";
import EmptyState from "@/components/EmptyState";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { btnPrimary, btnSecondary } from "@/lib/ui";
import Link from "next/link";

const PAGE_SIZE = 10;

// Remounted (key=status) each time the filter changes, so it always starts at page 1.
function ComplaintList({ status }) {
  const first = useApi("/complaints", { status, page: 1, limit: PAGE_SIZE });
  const [extra, setExtra] = useState([]); // items from "Show more"
  const [nextPage, setNextPage] = useState(2);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState("");

  async function showMore() {
    setLoadingMore(true);
    setMoreError("");
    try {
      const data = await api.get("/complaints", { status, page: nextPage, limit: PAGE_SIZE });
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

  if (!items.length)
    return status ? (
      <EmptyState title={`Nothing is "${STATUS_INFO[status].label.toLowerCase()}" right now`} text="Try another filter to see your other complaints." />
    ) : (
      <EmptyState
        title="You have not reported anything yet"
        text="Report an issue and it will show up here with its progress."
        actionHref="/citizen/report"
        actionLabel="Report an issue"
      />
    );

  return (
    <>
      <ul className="space-y-3">
        {items.map((c) => (
          <li key={c.id}>
            <ComplaintCard complaint={c} />
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

export default function MyComplaintsPage() {
  const [status, setStatus] = useState("");
  const filters = [{ value: "", label: "All" }, ...STATUS_ORDER.map((s) => ({ value: s, label: STATUS_INFO[s].label }))];

  return (
    <div>
      <PageHeader title="My complaints">
        <Link href="/citizen/report" className={btnPrimary}>
          Report an issue
        </Link>
      </PageHeader>

      <div role="group" aria-label="Filter by progress" className="mb-5 flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatus(f.value)}
            aria-pressed={status === f.value}
            className={`rounded-full border px-4 py-1.5 text-sm font-semibold ${
              status === f.value
                ? "border-asphalt bg-asphalt text-white"
                : "border-line bg-white text-asphalt hover:bg-concrete"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <ComplaintList key={status} status={status} />
    </div>
  );
}
