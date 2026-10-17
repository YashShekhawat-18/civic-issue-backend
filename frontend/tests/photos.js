// Real JPEG test photos (made with the backend's own writer): one with a GPS position, one without.
import fs from "node:fs";
import path from "node:path";

const dir = path.join(import.meta.dirname, "fixtures");
const make = (name, file) => new File([fs.readFileSync(path.join(dir, file))], name, { type: "image/jpeg" });

export const GPS_PHOTO_SPOT = { lat: 19.1867, lng: 73.192 };
export const gpsPhoto = () => make("at-the-spot.jpg", "photo-gps.jpg");
export const noGpsPhoto = () => make("no-location.jpg", "photo-nogps.jpg");
export const southWestPhoto = () => make("south-west.jpg", "photo-gps-south-west.jpg");
export const bytesOf = (file) => fs.readFileSync(path.join(dir, file === "gps" ? "photo-gps.jpg" : "photo-nogps.jpg"));
