import { readPhotoGps } from "./exif";

// Must match GEOTAG_MAX_DISTANCE_METERS on the backend (default 300).
export const MAX_PHOTO_DISTANCE_METERS = 300;

export const NO_GPS_MESSAGE =
  "This photo has no GPS location. Turn on location for your camera and take the photo again " +
  "(screenshots, downloaded pictures and PNG or WebP files have no location).";

/** Straight-line distance in metres between two {lat, lng} points (haversine formula). */
export function distanceMeters(a, b) {
  const R = 6371000;
  const rad = (d) => (d * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** 250 -> "250 m", 12231 -> "12.2 km" */
export function formatDistance(metres) {
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
}

/** "" when the photo position is close enough to the spot, otherwise a message saying what is wrong. */
export function photoPlaceProblem(photoGps, spot, placeLabel) {
  if (!photoGps) return NO_GPS_MESSAGE;
  if (!spot) return "";
  const metres = distanceMeters(photoGps, spot);
  if (metres > MAX_PHOTO_DISTANCE_METERS) {
    return `This photo was taken ${formatDistance(metres)} from ${placeLabel}. It must be within ${MAX_PHOTO_DISTANCE_METERS} m. Take the photo at the spot.`;
  }
  return "";
}

export { readPhotoGps };
