"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import ComplaintCard from "@/components/ComplaintCard";
import EmptyState from "@/components/EmptyState";
import BadgeStamp from "@/components/BadgeStamp";
import Alert from "@/components/Alert";
import { IconCamera, IconStar } from "@/components/icons";
import { btnGhost, plate } from "@/lib/ui";

function PointsCard() {
  const { data, error } = useApi("/gamification/me");
  if (error) return <Alert type="error">{error}</Alert>;
  const next = data?.nextBadge;
  const points = data?.points ?? 0;
  // How far along the way to the next badge (0 to 100).
  const progress = next ? Math.min(100, Math.round((points / next.pointsRequired) * 100)) : 100;
  return (
    <section className={`${plate} p-5`} aria-label="Your points">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Your points</h2>
        <Link href="/citizen/rewards" className={`${btnGhost} !px-2 !py-1`}>
          See rewards
        </Link>
      </div>
      <p className="mt-2 flex items-baseline gap-2">
        <IconStar size={22} className="self-center text-signal" />
        <span className="font-display text-5xl font-extrabold" data-testid="dashboard-points">
          {data ? points : "-"}
        </span>
      </p>
      {data && (
        <>
          <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-concrete" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Progress to next badge">
            <div className="h-full rounded-full bg-highway" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-2 text-sm text-asphalt-soft">
            {next
              ? `${next.pointsNeeded} more ${next.pointsNeeded === 1 ? "point" : "points"} to earn the ${next.name} badge.`
              : "You have earned every badge. Thank you for keeping your city in shape."}
          </p>
          {data.badges.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-3">
              {data.badges.slice(0, 3).map((b) => (
                <BadgeStamp key={b.name} badge={b} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function LatestComplaints() {
  const { data, error, loading } = useApi("/complaints", { limit: 3 });
  if (error) return <Alert type="error">{error}</Alert>;
  if (loading) return <div className="h-40 animate-pulse rounded-2xl bg-line" />;
  if (!data.items.length)
    return (
      <EmptyState
        title="You have not reported anything yet"
        text="Spotted a pothole, a broken light or a garbage pile? Report it and follow it here."
        actionHref="/citizen/report"
        actionLabel="Report your first issue"
      />
    );
  return (
    <ul className="space-y-3">
      {data.items.map((c) => (
        <li key={c.id}>
          <ComplaintCard complaint={c} />
        </li>
      ))}
    </ul>
  );
}

export default function CitizenHome() {
  const { user, refresh } = useAuth();
  useEffect(() => {
    refresh(); // keeps the points in the top bar up to date
  }, [refresh]);
  const firstName = user?.name?.split(" ")[0];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold">Hello, {firstName}</h1>

      <section className="rounded-2xl bg-signal p-6 md:flex md:items-center md:justify-between md:gap-6 md:p-8">
        <div>
          <h2 className="text-2xl font-extrabold md:text-3xl">See something broken?</h2>
          <p className="mt-1.5 max-w-md text-asphalt/80">
            Take a photo and mark the spot on the map. It goes straight to the right department.
          </p>
        </div>
        <Link
          href="/citizen/report"
          className="mt-5 inline-flex items-center gap-2 rounded-lg bg-asphalt px-5 py-3 font-semibold text-white hover:bg-black md:mt-0 md:shrink-0"
        >
          <IconCamera size={20} />
          Report an issue
        </Link>
      </section>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-5">
        <section className="min-w-0 md:col-span-3" aria-label="Your latest complaints">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-bold">Your latest complaints</h2>
            <Link href="/citizen/complaints" className={`${btnGhost} !px-2 !py-1`}>
              See all
            </Link>
          </div>
          <LatestComplaints />
        </section>
        <div className="min-w-0 md:col-span-2">
          <PointsCard />
        </div>
      </div>
    </div>
  );
}
