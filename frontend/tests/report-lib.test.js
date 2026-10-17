import { describe, expect, it } from "vitest";
import { buildReportFormData, validatePhoto, validateReport } from "@/lib/report";
import { photoSrc } from "@/lib/config";
import { gpsFromBytes, readPhotoGps } from "@/lib/exif";
import { distanceMeters, formatDistance, photoPlaceProblem, NO_GPS_MESSAGE } from "@/lib/geotag";
import { bytesOf, gpsPhoto, noGpsPhoto, southWestPhoto, GPS_PHOTO_SPOT } from "./photos";

const jpeg = new File([new Uint8Array(10)], "a.jpg", { type: "image/jpeg" });
const good = { categoryId: "c1", title: "Big pothole", description: "Deep pothole near bus stop", location: { lat: 19.07, lng: 72.87 }, photo: jpeg };

describe("validatePhoto", () => {
  it("accepts a JPEG", () => {
    expect(validatePhoto(new File([new Uint8Array(5)], "x.jpg", { type: "image/jpeg" }))).toBeNull();
  });
  it("rejects PNG and WebP because they cannot carry a location", () => {
    for (const type of ["image/png", "image/webp"]) expect(validatePhoto(new File([new Uint8Array(5)], "x", { type }))).toMatch(/JPEG.*location/);
  });
  it("rejects missing, wrong type, empty and oversized files", () => {
    expect(validatePhoto(null)).toMatch(/add a photo/);
    expect(validatePhoto(new File([new Uint8Array(5)], "x.gif", { type: "image/gif" }))).toMatch(/JPEG/);
    expect(validatePhoto(new File([], "x.jpg", { type: "image/jpeg" }))).toMatch(/empty/);
    const big = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "x.jpg", { type: "image/jpeg" });
    expect(validatePhoto(big)).toMatch(/too large/);
  });
});

describe("validateReport", () => {
  it("accepts a complete report", () => expect(validateReport(good)).toEqual({}));
  it("flags every missing field", () => {
    const e = validateReport({ categoryId: "", title: "abc", description: "short", location: null, photo: null });
    expect(Object.keys(e).sort()).toEqual(["categoryId", "description", "location", "photo", "title"]);
  });
  it("trims before counting and enforces maximums", () => {
    expect(validateReport({ ...good, title: "   ab   " }).title).toBeTruthy();
    expect(validateReport({ ...good, title: "x".repeat(151) }).title).toMatch(/150/);
    expect(validateReport({ ...good, description: "x".repeat(2001) }).description).toMatch(/2000/);
  });
});

describe("validateReport with the photo position", () => {
  it("accepts a photo taken at the pin", () => {
    expect(validateReport({ ...good, location: GPS_PHOTO_SPOT, photoGps: GPS_PHOTO_SPOT })).toEqual({});
  });
  it("rejects a photo with no GPS", () => {
    expect(validateReport({ ...good, photoGps: null }).photo).toBe(NO_GPS_MESSAGE);
  });
  it("rejects a photo taken too far from the pin", () => {
    const e = validateReport({ ...good, location: { lat: 19.2, lng: 73.192 }, photoGps: GPS_PHOTO_SPOT });
    expect(e.photo).toMatch(/taken 1\.[0-9] km from the pinned location/);
  });
  it("does not judge the photo position until it has been read", () => {
    expect(validateReport({ ...good, photoGps: undefined })).toEqual({});
  });
});

describe("reading GPS from a JPEG", () => {
  it("reads the position written by the backend (north-east)", async () => {
    const gps = await readPhotoGps(gpsPhoto());
    expect(gps.lat).toBeCloseTo(19.1867, 4);
    expect(gps.lng).toBeCloseTo(73.192, 4);
  });
  it("reads south and west as negative numbers", async () => {
    const gps = await readPhotoGps(southWestPhoto());
    expect(gps.lat).toBeCloseTo(-33.8688, 4);
    expect(gps.lng).toBeCloseTo(-70.6693, 4);
  });
  it("returns null for a photo with no GPS, a missing file and junk", async () => {
    expect(await readPhotoGps(noGpsPhoto())).toBeNull();
    expect(await readPhotoGps(null)).toBeNull();
    expect(gpsFromBytes(new Uint8Array([1, 2, 3]).buffer)).toBeNull();
    expect(gpsFromBytes(new ArrayBuffer(0))).toBeNull();
    const cut = bytesOf("gps").subarray(0, 40);
    expect(gpsFromBytes(cut.buffer.slice(cut.byteOffset, cut.byteOffset + cut.byteLength))).toBeNull();
  });
});

describe("distance and photo place check", () => {
  it("matches the backend formula", () => {
    expect(distanceMeters({ lat: 19, lng: 73 }, { lat: 19, lng: 73 })).toBe(0);
    expect(distanceMeters({ lat: 19, lng: 73 }, { lat: 19.001, lng: 73 })).toBeCloseTo(111.2, 0);
    expect(distanceMeters({ lat: 19, lng: 73 }, { lat: 19, lng: 73.001 })).toBeCloseTo(105.1, 0);
  });
  it("writes long distances in kilometres", () => {
    expect(formatDistance(250)).toBe("250 m");
    expect(formatDistance(999.4)).toBe("999 m");
    expect(formatDistance(12231)).toBe("12.2 km");
  });
  it("allows up to 300 m and blocks beyond", () => {
    const here = { lat: 19.0, lng: 73.0 };
    expect(photoPlaceProblem(here, { lat: 19.0026, lng: 73.0 }, "the spot")).toBe(""); // about 289 m
    expect(photoPlaceProblem(here, { lat: 19.0028, lng: 73.0 }, "the spot")).toMatch(/taken 3\d\d m from the spot/);
    expect(photoPlaceProblem(null, here, "the spot")).toBe(NO_GPS_MESSAGE);
  });
});

describe("buildReportFormData", () => {
  it("uses the exact field names the backend expects", () => {
    const fd = buildReportFormData({ ...good, title: "  Big pothole ", isAnonymous: true });
    expect(fd.get("title")).toBe("Big pothole");
    expect(fd.get("categoryId")).toBe("c1");
    expect(fd.get("latitude")).toBe("19.07");
    expect(fd.get("longitude")).toBe("72.87");
    expect(fd.get("isAnonymous")).toBe("true");
    expect(fd.get("photo")).toBeInstanceOf(File);
    expect(buildReportFormData({ ...good, isAnonymous: false }).get("isAnonymous")).toBe("false");
  });
});

describe("photoSrc", () => {
  it("prefixes the backend address for relative paths only", () => {
    expect(photoSrc("/uploads/x.jpg")).toBe("http://localhost:8000/uploads/x.jpg");
    expect(photoSrc("https://cdn.example.com/x.jpg")).toBe("https://cdn.example.com/x.jpg");
    expect(photoSrc("")).toBe("");
  });
});
