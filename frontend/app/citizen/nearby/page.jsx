"use client";

import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import MapView from "@/components/MapViewLoader";
import StatusPill from "@/components/StatusPill";
import UpvoteButton from "@/components/UpvoteButton";
import PageHeader from "@/components/PageHeader";
import EmptyState from "@/components/EmptyState";
import Alert from "@/components/Alert";
import { photoSrc } from "@/lib/config";
import { plural } from "@/lib/format";
import { btnPrimary, plate } from "@/lib/ui";
import { IconPin } from "@/components/icons";

const INDIA = { lat: 20.5937, lng: 78.9629 };
const RADII = [250, 500, 1000, 2000];

export default function NearbyPage() {
  const [center, setCenter] = useState(null);
  const [radius, setRadius] = useState(500);
  const [categoryId, setCategoryId] = useState("");
  const [geoMessage, setGeoMessage] = useState("");
  const [locating, setLocating] = useState(false);

  const { data: categories } = useApi("/categories");
  const { data, error, loading } = useApi(
    center ? "/complaints/nearby" : null,
    center ? { latitude: center.lat, longitude: center.lng, radius, categoryId } : undefined
  );

  function useMyLocation() {
    setGeoMessage("");
    if (!navigator.geolocation) {
      setGeoMessage("Your browser cannot detect location. Click on the map instead.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        setCenter({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      (err) => {
        setLocating(false);
        setGeoMessage(
          err.code === 1
            ? "Location permission was denied. Click on the map to choose where to look."
            : "Could not detect your location. Click on the map to choose where to look."
        );
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  const items = data?.items ?? [];
  const markers = items.map((c) => ({
    id: c.id,
    lat: c.location.coordinates[1],
    lng: c.location.coordinates[0],
    status: c.status,
    title: c.title,
  }));

  return (
    <div>
      <PageHeader title="Issues near you" />
      <p className="-mt-3 mb-5 max-w-xl text-asphalt-soft">
        See what neighbours have already reported. If your problem is on the list, upvote it instead of reporting it again.
      </p>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <button type="button" onClick={useMyLocation} disabled={locating} className={btnPrimary}>
          <IconPin size={18} />
          {locating ? "Detecting..." : "Use my location"}
        </button>
        <div>
          <label htmlFor="radius" className="mb-1 block text-xs font-semibold text-asphalt-soft">
            Distance
          </label>
          <select id="radius" value={radius} onChange={(e) => setRadius(Number(e.target.value))} className="rounded-lg border border-line bg-white px-3 py-2.5 text-sm">
            {RADII.map((r) => (
              <option key={r} value={r}>
                {r >= 1000 ? `${r / 1000} km` : `${r} m`}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="category" className="mb-1 block text-xs font-semibold text-asphalt-soft">
            Category
          </label>
          <select id="category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="rounded-lg border border-line bg-white px-3 py-2.5 text-sm">
            <option value="">All categories</option>
            {(categories || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {geoMessage && <p className="mb-3 text-sm text-amber-800">{geoMessage}</p>}

      <MapView
        center={center || INDIA}
        zoom={center ? 15 : 5}
        radius={center ? radius : undefined}
        markers={markers}
        onPick={setCenter}
        showCenter={!!center}
        label="Map of nearby issues. Click to choose where to look."
        height={320}
      />
      <p className="mb-6 mt-2 text-sm text-asphalt-soft" data-testid="nearby-hint">
        {center ? "Click the map to look somewhere else." : "Use your location, or click the map to choose where to look."}
      </p>

      {error && <Alert type="error">{error}</Alert>}
      {center && loading && <div className="h-24 animate-pulse rounded-2xl bg-line" />}
      {center && data && !items.length && (
        <EmptyState title="Nothing reported here yet" text="No open complaints in this area. If you see a problem, you can be the first to report it." actionHref="/citizen/report" actionLabel="Report an issue" />
      )}
      {items.length > 0 && (
        <section aria-label="Complaints near this spot">
          <h2 className="mb-3 text-xl font-bold">{plural(items.length, "complaint", "complaints")} nearby</h2>
          <ul className="space-y-3">
            {items.map((c) => (
              <li key={c.id} className={`${plate} flex gap-3 p-4`}>
                {c.photoUrl && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={photoSrc(c.photoUrl)} alt="" className="h-20 w-20 shrink-0 rounded-lg object-cover" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold">{c.title}</h3>
                    <StatusPill status={c.status} overdue={c.overdue} />
                  </div>
                  <p className="mt-0.5 text-sm text-asphalt-soft">
                    {c.category?.name}, {c.distanceMeters} m away
                    {c.reporter?.name ? `, reported by ${c.reporter.name}` : ""}
                  </p>
                  <div className="mt-3">
                    {c.isOwnComplaint ? (
                      <span className="rounded-full bg-sign-tint px-3 py-1 text-xs font-bold text-sign">Your complaint</span>
                    ) : (
                      <UpvoteButton complaintId={c.id} initialCount={c.upvoteCount} initialUpvoted={c.hasUpvoted} />
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
