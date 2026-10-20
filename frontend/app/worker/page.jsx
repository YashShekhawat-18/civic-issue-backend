"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import TaskCard from "@/components/TaskCard";
import Alert from "@/components/Alert";
import EmptyState from "@/components/EmptyState";
import { btnGhost, plate } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";

// A big number that is also a shortcut to the matching list.
function Tile({ id, href, label, query, tone }) {
  const { data, error, loading } = useApi("/worker/complaints", { ...query, limit: 1 });
  return (
    <Link href={href} className={`${plate} block p-5 transition-shadow hover:shadow-md`}>
      <p className="text-sm font-semibold text-asphalt-soft">{label}</p>
      <p className={`mt-1 text-4xl font-extrabold ${tone}`} data-testid={`tile-${id}`}>
        {error ? "-" : loading ? "..." : data.total}
      </p>
    </Link>
  );
}

function ShortList({ title, query, href, emptyTitle, emptyText }) {
  const t = useT();
  const { data, error, loading } = useApi("/worker/complaints", { ...query, limit: 5 });
  return (
    <section aria-label={title}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-bold">{title}</h2>
        <Link href={href} className={btnGhost}>
          {t("See all")}
        </Link>
      </div>
      {error ? (
        <Alert type="error">{error}</Alert>
      ) : loading ? (
        <div className="h-32 animate-pulse rounded-2xl bg-line" />
      ) : data.items.length ? (
        <ul className="space-y-3">
          {data.items.map((task) => (
            <li key={task.id}>
              <TaskCard task={task} />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={emptyTitle} text={emptyText} />
      )}
    </section>
  );
}

export default function WorkerHome() {
  const t = useT();
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold">Hello, {firstName}</h1>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Tile id="new" href="/worker/tasks?filter=new" label={t("Waiting for a worker")} query={{ status: "SUBMITTED" }} tone="text-sign" />
        <Tile id="mine" href="/worker/tasks?filter=mine" label={t("Your jobs in progress")} query={{ status: "IN_PROGRESS", assignedToMe: "true" }} tone="text-asphalt" />
        <Tile id="overdue" href="/worker/tasks?filter=overdue" label={t("Overdue")} query={{ overdue: "true" }} tone="text-flag" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="min-w-0">
          <ShortList
            title={t("Your jobs in progress")}
            query={{ status: "IN_PROGRESS", assignedToMe: "true" }}
            href="/worker/tasks?filter=mine"
            emptyTitle="You have no jobs in progress"
            emptyText="Open a new report and choose Start work to take it."
          />
        </div>
        <div className="min-w-0">
          <ShortList
            title={t("Newest reports")}
            query={{ status: "SUBMITTED" }}
            href="/worker/tasks?filter=new"
            emptyTitle="No new reports"
            emptyText="Everything in your department has been picked up."
          />
        </div>
      </div>
    </div>
  );
}
