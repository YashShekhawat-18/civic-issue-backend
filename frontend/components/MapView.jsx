"use client";

import { useEffect } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { useT } from "@/context/LanguageContext";

const COLORS = { SUBMITTED: "#1d5fd1", IN_PROGRESS: "#f6b400", RESOLVED: "#0b6b4d", HERE: "#1b2430" };

function pinIcon(color, big = false) {
  const size = big ? 26 : 20;
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;background:${color};border:3px solid #fff;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 1px 4px rgba(0,0,0,.5)"></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

function Picker({ onPick }) {
  useMapEvents({ click: (e) => onPick({ lat: e.latlng.lat, lng: e.latlng.lng }) });
  return null;
}

// Moves the map when the centre changes (for example after "Use my location").
function Recenter({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([center.lat, center.lng], zoom ?? map.getZoom(), { duration: 0.6 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center.lat, center.lng]);
  return null;
}

/**
 * Read-only map with coloured pins.
 *  center   {lat, lng}
 *  markers  [{id, lat, lng, status, title, href}]
 *  radius   metres, draws a circle around the centre
 *  onPick   optional: called with {lat, lng} when the map is clicked
 *  showCenter  draw a dark pin at the centre
 */
export default function MapView({ center, zoom = 15, markers = [], radius, onPick, showCenter = false, height = 288, label = "Map" }) {
  const t = useT();
  return (
    <div
      data-testid="map"
      role="region"
      aria-label={label}
      className="overflow-hidden rounded-2xl border border-line"
      style={{ height }}
    >
      <MapContainer center={[center.lat, center.lng]} zoom={zoom} scrollWheelZoom={!!onPick} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">{t("OpenStreetMap")}</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {onPick && <Picker onPick={onPick} />}
        <Recenter center={center} zoom={zoom} />
        {radius ? (
          <Circle center={[center.lat, center.lng]} radius={radius} pathOptions={{ color: "#0b6b4d", weight: 2, fillOpacity: 0.06 }} />
        ) : null}
        {showCenter && <Marker position={[center.lat, center.lng]} icon={pinIcon(COLORS.HERE, true)} />}
        {markers.map((m) => (
          <Marker key={m.id} position={[m.lat, m.lng]} icon={pinIcon(COLORS[m.status] || COLORS.SUBMITTED)}>
            {m.title && (
              <Popup>
                <strong>{m.title}</strong>
                {m.href && (
                  <>
                    <br />
                    <a href={m.href}>{t("Open")}</a>
                  </>
                )}
              </Popup>
            )}
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
