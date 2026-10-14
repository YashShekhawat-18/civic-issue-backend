import { describe, expect, it } from "vitest";
import { buildReportFormData, validatePhoto, validateReport } from "@/lib/report";
import { photoSrc } from "@/lib/config";

const png = new File([new Uint8Array(10)], "a.png", { type: "image/png" });
const good = { categoryId: "c1", title: "Big pothole", description: "Deep pothole near bus stop", location: { lat: 19.07, lng: 72.87 }, photo: png };

describe("validatePhoto", () => {
  it("accepts jpeg/png/webp", () => {
    for (const type of ["image/jpeg", "image/png", "image/webp"]) expect(validatePhoto(new File([new Uint8Array(5)], "x", { type }))).toBeNull();
  });
  it("rejects missing, wrong type, empty and oversized files", () => {
    expect(validatePhoto(null)).toMatch(/add a photo/);
    expect(validatePhoto(new File([new Uint8Array(5)], "x.gif", { type: "image/gif" }))).toMatch(/JPEG/);
    expect(validatePhoto(new File([], "x.png", { type: "image/png" }))).toMatch(/empty/);
    const big = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "x.png", { type: "image/png" });
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
