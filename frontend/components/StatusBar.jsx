"use client";

import { share } from "@/lib/charts";
import { STATUS_INFO } from "@/lib/status";
import { useT } from "@/context/LanguageContext";

// The status colours are the same ones used on the pills and the progress road everywhere in the app.
const FILL = { SUBMITTED: "bg-sign", IN_PROGRESS: "bg-signal", RESOLVED: "bg-highway" };

/**
 * Part of the whole: one bar split into Reported / Being fixed / Resolved with a 2px gap between
 * segments. The legend below always shows the name and number, so colour is never the only clue.
 */
export default function StatusBar({ rows }) {
  const t = useT();
  const total = rows.reduce((sum, r) => sum + r.count, 0);
  if (!total) return <p className="text-sm text-asphalt-soft">{t("No complaints yet.")}</p>;

  return (
    <div>
      <div role="img" aria-label={rows.map((r) => `${STATUS_INFO[r.status].label}: ${r.count}`).join(", ")} className="flex h-5 gap-0.5">
        {rows
          .filter((r) => r.count > 0)
          .map((r) => (
            <div
              key={r.status}
              title={`${STATUS_INFO[r.status].label}: ${r.count} (${share(r.count, total)}%)`}
              className={`${FILL[r.status]} rounded-[4px] transition-[filter] hover:brightness-110`}
              style={{ flexGrow: r.count, flexBasis: 0 }}
            />
          ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-sm">
        {rows.map((r) => (
          <li key={r.status} className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-sm ${FILL[r.status]}`} aria-hidden="true" />
            <span className="text-asphalt-soft">{STATUS_INFO[r.status].label}</span>
            <strong className="tabular-nums">{r.count}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}
