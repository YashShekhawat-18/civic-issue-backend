"use client";

import { useT } from "@/context/LanguageContext";
import { statusInfo } from "@/lib/status";

export default function StatusPill({ status, overdue }) {
  const t = useT();
  const info = statusInfo(status);
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${info.pill}`}>{t(info.label)}</span>
      {overdue && status !== "RESOLVED" && (
        <span className="rounded-full bg-flag px-2.5 py-1 text-xs font-bold text-white">{t("Overdue")}</span>
      )}
    </span>
  );
}
