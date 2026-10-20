"use client";

import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { fitView } from "@/lib/charts";
import { STATUS_INFO, STATUS_ORDER } from "@/lib/status";
import MapView from "@/components/MapViewLoader";
import PageHeader from "@/components/PageHeader";
import Alert from "@/components/Alert";
import { plate } from "@/lib/ui";
import { useT } from "@/context/LanguageContext";

// Same colours as the pins on the map.
const SWATCH = { SUBMITTED: "bg-sign", IN_PROGRESS: "bg-signal", RESOLVED: "bg-highway" };
const field = "rounded-lg border border-line bg-white px-3 py-2 text-sm";

export default function AdminMapPage() {
  const t = useT();
  const [status, setStatus] = useState("");
  const [overdue, setOverdue] = useState(false);
  const { data, error, loading } = useApi("/admin/complaints/map", { status, overdue: overdue ? "true" : "", limit: 500 });

  const items = data?.items || [];
  const points = items.map((i) => ({ lat: i.latitude, lng: i.longitude }));
  const view = fitView(points);
  const counts = STATUS_ORDER.map((s) => ({ s, n: items.filter((i) => i.status === s).length }));

  return (
    <div>
      <PageHeader title={t("Complaint map")} />

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <label className="text-sm font-semibold">
          {t("Progress")}
          <select className={`${field} mt-1 block font-normal`} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("All")}</option>
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {STATUS_INFO[s].label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm font-semibold">
          <input type="checkbox" checked={overdue} onChange={(e) => setOverdue(e.target.checked)} />
          {t("Only overdue")}
        </label>
      </div>

      <Alert type="error">{error}</Alert>

      <div className={loading && data ? "opacity-60" : ""}>
        <MapView
          // The map keeps its place while filters change; it only re-centres when the pins move.
          center={view.center}
          zoom={view.zoom}
          height={460}
          label={t("All complaints")}
          markers={items.map((i) => ({
            id: i.id,
            lat: i.latitude,
            lng: i.longitude,
            status: i.status,
            title: `${i.complaintNumber}: ${i.title}`,
            href: `/admin/complaints/${i.id}`,
          }))}
        />
      </div>

      <section className={`${plate} mt-4 p-4`} aria-label={t("Map key")}>
        <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          {counts.map(({ s, n }) => (
            <li key={s} className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded-full ${SWATCH[s]}`} aria-hidden="true" />
              {STATUS_INFO[s].label}
              <strong data-testid={`pins-${s}`}>{n}</strong>
            </li>
          ))}
        </ul>
        {data && data.count >= data.limit && (
          <p className="mt-2 text-xs text-asphalt-soft">Showing the newest {data.limit} complaints. Use a filter to narrow it down.</p>
        )}
        {data && items.length === 0 && <p className="mt-2 text-sm text-asphalt-soft">{t("No complaints match these filters.")}</p>}
      </section>
    </div>
  );
}
