"use client";

import dynamic from "next/dynamic";

// Leaflet needs the browser window, so it is never rendered on the server.
const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => <div className="h-72 animate-pulse rounded-2xl bg-line" />,
});

export default MapView;
