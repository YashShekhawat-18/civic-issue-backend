"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/context/AuthContext";
import { foldTail } from "@/lib/charts";
import StatTile from "@/components/StatTile";
import BarList from "@/components/BarList";
import StatusBar from "@/components/StatusBar";
import TaskCard from "@/components/TaskCard";
import Alert from "@/components/Alert";
import EmptyState from "@/components/EmptyState";
import Spinner from "@/components/Spinner";
import { btnGhost, btnSecondary, plate } from "@/lib/ui";

function CardList({ title, items, href, empty }) {
  return (
    <section aria-label={title} className="min-w-0">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-bold">{title}</h2>
        {href && (
          <Link href={href} className={btnGhost}>
            See all
          </Link>
        )}
      </div>
      {items.length ? (
        <ul className="space-y-3">
          {items.map((c) => (
            <li key={c.id}>
              <TaskCard task={c} base="/admin/complaints" showDepartment />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={empty.title} text={empty.text} />
      )}
    </section>
  );
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useApi("/admin/dashboard");
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

  if (loading && !data) return <Spinner />;
  if (error && !data) return <Alert type="error">{error}</Alert>;

  const t = data.totals;
  const rate = data.resolutionRatePercent;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-3xl font-extrabold">Hello, {user?.name?.split(" ")[0]}</h1>
        <button onClick={runCheck} disabled={check.busy} className={btnSecondary}>
          {check.busy ? "Checking..." : "Run overdue check now"}
        </button>
      </div>
      <Alert type="success">{check.message}</Alert>
      <Alert type="error">{check.error}</Alert>

      <section className={`${plate} grid gap-6 p-5 md:grid-cols-[auto_1fr] md:items-center md:gap-10 md:p-6`} aria-label="Resolution rate">
        <div>
          <p className="text-sm font-semibold text-asphalt-soft">Resolution rate</p>
          <p className="text-6xl font-extrabold leading-none" data-testid="resolution-rate">
            {rate}%
          </p>
          <p className="mt-1 text-sm text-asphalt-soft">of {t.total} complaints are resolved</p>
        </div>
        <StatusBar rows={data.byStatus} />
      </section>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5 [&>*:last-child:nth-child(odd)]:col-span-2 md:[&>*:last-child:nth-child(odd)]:col-span-1">
        <StatTile id="total" label="All complaints" value={t.total} href="/admin/complaints" />
        <StatTile id="submitted" label="Reported" value={t.submitted} href="/admin/complaints?status=SUBMITTED" tone="text-sign" />
        <StatTile id="inProgress" label="Being fixed" value={t.inProgress} href="/admin/complaints?status=IN_PROGRESS" />
        <StatTile id="resolved" label="Resolved" value={t.resolved} href="/admin/complaints?status=RESOLVED" tone="text-highway" />
        <StatTile id="overdue" label="Overdue" value={t.overdue} href="/admin/overdue" tone="text-flag" />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <BarList title="By department" subtitle="Where complaints go" rows={foldTail(data.byDepartment)} />
        <BarList title="By category" subtitle="What people report" rows={foldTail(data.byCategory)} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CardList
          title="Oldest overdue"
          items={data.oldestOverdue}
          href="/admin/overdue"
          empty={{ title: "Nothing is overdue", text: "Every open complaint is within the time limit." }}
        />
        <CardList
          title="Newest complaints"
          items={data.recentComplaints}
          href="/admin/complaints"
          empty={{ title: "No complaints yet", text: "They will appear here as citizens report issues." }}
        />
      </div>
    </div>
  );
}
