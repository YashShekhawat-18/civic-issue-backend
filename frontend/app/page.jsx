"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { homeFor } from "@/lib/roles";
import Spinner from "@/components/Spinner";
import RoadTracker from "@/components/RoadTracker";
import { useT } from "@/context/LanguageContext";
import { btnPrimary, btnSecondary, plate } from "@/lib/ui";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const t = useT();

  useEffect(() => {
    if (!loading && user) router.replace(homeFor(user.role));
  }, [loading, user, router]);

  if (loading || user) return <Spinner />;

  return (
    <div className="grid items-center gap-10 py-6 md:grid-cols-2 md:py-14">
      <section>
        <h1 className="text-4xl font-extrabold leading-[1.1] sm:text-5xl">
          {t("Report it. Watch it get fixed.")}
        </h1>
        <p className="mt-4 max-w-md text-lg text-asphalt-soft">
          {t("Potholes, garbage, broken streetlights, water leaks. Send them to the right department with a photo and a pin, then follow every step until the work is done.")}
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link href="/register" className={`${btnPrimary} !px-6 !py-3 !text-base`}>
            {t("Create an account")}
          </Link>
          <Link href="/login" className={`${btnSecondary} !px-6 !py-3 !text-base`}>
            {t("Log in")}
          </Link>
        </div>
        <p className="mt-5 text-sm text-asphalt-soft">
          {t("City staff?")}{" "}
          <Link href="/login?as=worker" className="font-semibold text-sign hover:underline">{t("Worker log in")}</Link>
          {" / "}
          <Link href="/login?as=admin" className="font-semibold text-sign hover:underline">{t("Admin log in")}</Link>
        </p>
      </section>

      <section aria-label="Example complaint" className={`${plate} p-5 shadow-sm`}>
        <p className="text-sm font-semibold text-asphalt-soft">CIV-2026-000128</p>
        <h2 className="mt-0.5 text-xl font-bold">{t("Large pothole near the bus stop")}</h2>
        <p className="mt-1 text-sm text-asphalt-soft">{t("Roads department, reported 2 days ago")}</p>
        <div className="mt-6 px-1 pb-1">
          <RoadTracker status="IN_PROGRESS" />
        </div>
        <p className="mt-4 rounded-lg bg-signal-tint px-3 py-2 text-sm font-medium">{t("A worker is on it.")}</p>
      </section>
    </div>
  );
}
