import { describe, expect, it } from "vitest";
import { formatDate, plural, timeAgo } from "@/lib/format";
import { STATUS_ORDER, statusIndex, statusInfo } from "@/lib/status";

describe("timeAgo", () => {
  const now = Date.parse("2026-10-15T12:00:00Z");
  it("uses plain words", () => {
    expect(timeAgo("2026-10-15T11:59:50Z", now)).toBe("just now");
    expect(timeAgo("2026-10-15T11:59:00Z", now)).toBe("1 minute ago");
    expect(timeAgo("2026-10-15T09:00:00Z", now)).toBe("3 hours ago");
    expect(timeAgo("2026-10-13T12:00:00Z", now)).toBe("2 days ago");
  });
  it("falls back to a date after a month, and handles bad input", () => {
    expect(timeAgo("2026-08-01T12:00:00Z", now)).toMatch(/2026/);
    expect(timeAgo("", now)).toBe("");
    expect(timeAgo("not a date", now)).toBe("");
    expect(formatDate("garbage")).toBe("");
  });
  it("never shows a negative time for dates in the future", () => {
    expect(timeAgo("2026-10-15T12:05:00Z", now)).toBe("just now");
  });
});

describe("plural", () => {
  it("handles one and many", () => {
    expect(plural(1, "upvote", "upvotes")).toBe("1 upvote");
    expect(plural(0, "upvote", "upvotes")).toBe("0 upvotes");
    expect(plural(5, "person", "people")).toBe("5 people");
  });
});

describe("status helpers", () => {
  it("matches the three backend statuses, in order", () => {
    expect(STATUS_ORDER).toEqual(["SUBMITTED", "IN_PROGRESS", "RESOLVED"]);
    expect(STATUS_ORDER.map((s) => statusInfo(s).label)).toEqual(["Reported", "Being fixed", "Resolved"]);
  });
  it("does not crash on an unknown status", () => {
    expect(statusInfo("WEIRD").label).toBe("WEIRD");
    expect(statusIndex("WEIRD")).toBe(0);
    expect(statusIndex("RESOLVED")).toBe(2);
  });
});
