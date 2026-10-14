"use client";

import { useEffect, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

// A plain CSS pin, so we do not depend on Leaflet's default image files (which break with bundlers).
const pin = L.divIcon({
  className: "",
  html: '<div style="width:22px;height:22px;background:#dc2626;border:3px solid #fff;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 1px 4px rgba(0,0,0,.5)"></div>',
  iconSize: [22, 22],
  iconAnchor: [11, 22],
});

const INDIA_CENTER = [20.5937, 78.9629];

function ClickToPick({ onChange }) {
  useMapEvents({
    click(e) {
      onChange({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  return null;
}

function FlyToValue({ value }) {
  const map = useMap();
  useEffect(() => {
    if (value) map.flyTo([value.lat, value.lng], Math.max(map.getZoom(), 16), { duration: 0.6 });
    // only when a new point is chosen
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value?.lat, value?.lng]);
  return null;
}

export default function LocationPicker({ value, onChange, error }) {
  const [geoMessage, setGeoMessage] = useState("");
  const [locating, setLocating] = useState(false);

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
        onChange({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      (err) => {
        setLocating(false);
        setGeoMessage(
          err.code === 1
            ? "Location permission was denied. Click on the map to choose the spot."
            : "Could not detect your location. Click on the map to choose the spot."
        );
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={useMyLocation}
          disabled={locating}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100 disabled:opacity-60"
        >
          {locating ? "Detecting..." : "Use my current location"}
        </button>
        <span className="text-sm text-slate-600" data-testid="coords">
          {value ? `Selected: ${value.lat.toFixed(5)}, ${value.lng.toFixed(5)}` : "Or click on the map to drop a pin"}
        </span>
      </div>
      <div
        data-testid="map"
        className={`h-72 overflow-hidden rounded-md border ${error ? "border-red-400" : "border-slate-300"}`}
      >
        <MapContainer
          center={value ? [value.lat, value.lng] : INDIA_CENTER}
          zoom={value ? 16 : 5}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickToPick onChange={onChange} />
          <FlyToValue value={value} />
          {value && (
            <Marker
              position={[value.lat, value.lng]}
              icon={pin}
              draggable
              eventHandlers={{
                dragend(e) {
                  const p = e.target.getLatLng();
                  onChange({ lat: p.lat, lng: p.lng });
                },
              }}
            />
          )}
        </MapContainer>
      </div>
      {geoMessage && <p className="mt-1 text-xs text-amber-700">{geoMessage}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}
