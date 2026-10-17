// Small helpers for the admin charts.

/** Keeps the biggest `max` rows and folds the rest into one "Other" row, so a chart never needs a 9th colour. */
export function foldTail(rows, max = 8) {
  if (rows.length <= max) return rows;
  const head = rows.slice(0, max - 1);
  const rest = rows.slice(max - 1);
  return [...head, { id: "other", name: "Other", count: rest.reduce((sum, r) => sum + r.count, 0) }];
}

export function share(count, total) {
  return total ? Math.round((count * 1000) / total) / 10 : 0;
}

/** 1284 -> "1,284", 12900 -> "12.9K" */
export function compact(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 10_000) return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}K`;
  return n.toLocaleString("en-IN");
}

/** A centre and zoom that show every pin on the map. */
export function fitView(points) {
  if (!points.length) return { center: { lat: 20.5937, lng: 78.9629 }, zoom: 5 };
  const lats = points.map((p) => p.lat);
  const lngs = points.map((p) => p.lng);
  const spread = Math.max(Math.max(...lats) - Math.min(...lats), Math.max(...lngs) - Math.min(...lngs));
  const zoom = spread < 0.005 ? 16 : spread < 0.03 ? 14 : spread < 0.15 ? 12 : spread < 0.6 ? 10 : spread < 3 ? 8 : spread < 10 ? 6 : 5;
  return {
    center: { lat: (Math.min(...lats) + Math.max(...lats)) / 2, lng: (Math.min(...lngs) + Math.max(...lngs)) / 2 },
    zoom,
  };
}
