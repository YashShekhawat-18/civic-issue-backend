"use client";

import { useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import BadgeStamp from "@/components/BadgeStamp";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import Spinner from "@/components/Spinner";
import { IconStar } from "@/components/icons";
import { formatDate } from "@/lib/format";
import { useT } from "@/context/LanguageContext";
import { plate } from "@/lib/ui";

const EVENTS = {
  COMPLAINT_CREATED: "You reported an issue",
  COMPLAINT_UPVOTED: "Neighbours upvoted your complaint",
  COMPLAINT_RESOLVED: "Your complaint was resolved",
};

export default function RewardsPage() {
  const t = useT();
  const { user, refresh } = useAuth();
  const me = useApi("/gamification/me");
  const badges = useApi("/gamification/badges");
  const board = useApi("/gamification/leaderboard", { limit: 10 });

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (me.loading || badges.loading) return <Spinner />;
  if (me.error || badges.error) return <Alert type="error">{me.error || badges.error}</Alert>;

  const earned = new Set(me.data.badges.map((b) => b.name));
  const next = me.data.nextBadge;

  return (
    <div className="space-y-6">
      <PageHeader title="Rewards" />

      <section className={`${plate} p-6`}>
        <p className="flex items-center gap-2 text-sm font-semibold text-asphalt-soft">
          <IconStar size={16} className="text-signal" /> {t("Total points")}
        </p>
        <p className="font-display text-6xl font-extrabold" data-testid="rewards-points">
          {me.data.points}
        </p>
        <p className="mt-1 text-asphalt-soft">
          {next
            ? t(next.pointsNeeded === 1 ? "{n} more point to earn the {badge} badge." : "{n} more points to earn the {badge} badge.", { n: next.pointsNeeded, badge: next.name })
            : t("You have earned every badge.")}
        </p>
      </section>

      <section aria-label={t("Badges")}>
        <h2 className="mb-3 text-xl font-bold">{t("Badges")}</h2>
        {badges.data.length ? (
          <div className="flex flex-wrap gap-4">
            {badges.data.map((b) => (
              <BadgeStamp key={b.name} badge={b} earned={earned.has(b.name)} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-asphalt-soft">{t("No badges have been set up yet.")}</p>
        )}
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section aria-label={t("Recent activity")} className={`${plate} p-5`}>
          <h2 className="text-lg font-bold">{t("Recent points")}</h2>
          {me.data.recentActivity.length ? (
            <ul className="mt-3 divide-y divide-line">
              {me.data.recentActivity.map((a, i) => (
                <li key={i} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                  <span>
                    {t(EVENTS[a.event] || "Points earned")}
                    <span className="block text-xs text-asphalt-soft">{formatDate(a.createdAt)}</span>
                  </span>
                  <span className="font-bold text-highway">+{a.points}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-asphalt-soft">{t("Report an issue to earn your first points.")}</p>
          )}
        </section>

        <section aria-label={t("Leaderboard")} className={`${plate} p-5`}>
          <h2 className="text-lg font-bold">{t("Top citizens")}</h2>
          {board.error ? (
            <p className="mt-2 text-sm text-flag">{board.error}</p>
          ) : board.data?.length ? (
            <ol className="mt-3 divide-y divide-line">
              {board.data.map((p) => (
                <li key={p.rank} className={`flex items-center gap-3 py-2.5 text-sm ${p.name === user?.name ? "font-bold" : ""}`}>
                  <span className="w-6 text-asphalt-soft">{p.rank}</span>
                  <span className="min-w-0 flex-1 truncate">{p.name}</span>
                  <span>{p.points}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-2 text-sm text-asphalt-soft">{t("Nobody has points yet. Be the first.")}</p>
          )}
        </section>
      </div>
    </div>
  );
}
