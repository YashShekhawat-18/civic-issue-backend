"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { IconAward, IconBell, IconFlag, IconWrench } from "@/components/icons";
import { timeAgo } from "@/lib/format";
import { announceNotificationsChanged } from "@/lib/events";
import { useT } from "@/context/LanguageContext";
import { btnSecondary } from "@/lib/ui";

const KINDS = {
  STATUS_CHANGED: { Icon: IconWrench, tone: "bg-sign-tint text-sign" },
  COMPLAINT_OVERDUE: { Icon: IconFlag, tone: "bg-flag-tint text-flag" },
  BADGE_EARNED: { Icon: IconAward, tone: "bg-signal-tint text-asphalt" },
};

export default function NotificationsPage() {
  const t = useT();
  const { data, error, loading, reload } = useApi("/notifications", { limit: 50 });
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);

  async function markAllRead() {
    setBusy(true);
    setActionError("");
    try {
      await api.patch("/notifications/read-all");
      reload();
      announceNotificationsChanged();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function markRead(n) {
    if (n.isRead) return;
    try {
      await api.patch(`/notifications/${n.id}/read`);
      reload();
      announceNotificationsChanged();
    } catch {
      /* opening the complaint still works; the unread dot will clear next time */
    }
  }

  if (loading && !data) return <Spinner />;
  if (error) return <Alert type="error">{error}</Alert>;

  return (
    <div>
      <PageHeader title="Alerts">
        {data.unreadCount > 0 && (
          <button onClick={markAllRead} disabled={busy} className={btnSecondary}>
            {t("Mark all as read")}
          </button>
        )}
      </PageHeader>
      <Alert type="error">{actionError}</Alert>

      {!data.items.length ? (
        <EmptyState title="No alerts yet" text="You will see a message here when the status of your complaint changes or when you earn a badge." />
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-white">
          {data.items.map((n) => {
            const kind = KINDS[n.type] || { Icon: IconBell, tone: "bg-concrete text-asphalt" };
            const body = (
              <div className="flex gap-3 p-4">
                <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${kind.tone}`}>
                  <kind.Icon size={18} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className={`${n.isRead ? "font-medium" : "font-bold"}`}>{n.title}</p>
                  <p className="mt-0.5 text-sm text-asphalt-soft">{n.message}</p>
                  <p className="mt-1 text-xs text-asphalt-soft">{timeAgo(n.createdAt)}</p>
                </div>
                {!n.isRead && <span aria-label={t("Unread")} className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full bg-sign" />}
              </div>
            );
            return (
              <li key={n.id} className={n.isRead ? "" : "bg-sign-tint/40"}>
                {n.complaintId ? (
                  <Link href={`/citizen/complaints/${n.complaintId}`} onClick={() => markRead(n)} className="block hover:bg-concrete/60">
                    {body}
                  </Link>
                ) : (
                  <button type="button" onClick={() => markRead(n)} className="block w-full text-left hover:bg-concrete/60">
                    {body}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
