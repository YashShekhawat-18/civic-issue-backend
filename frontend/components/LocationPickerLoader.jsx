"use client";

import dynamic from "next/dynamic";

// Leaflet touches `window`, so it must only load in the browser (never during server rendering).
const LocationPicker = dynamic(() => import("./LocationPicker"), {
  ssr: false,
  loading: () => <div className="h-72 animate-pulse rounded-md bg-slate-200" />,
});

export default LocationPicker;
