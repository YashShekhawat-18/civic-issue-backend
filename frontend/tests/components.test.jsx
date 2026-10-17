import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));

import RoadTracker from "@/components/RoadTracker";
import ComplaintCard from "@/components/ComplaintCard";
import UpvoteButton from "@/components/UpvoteButton";
import StatusPill from "@/components/StatusPill";
import BadgeStamp from "@/components/BadgeStamp";

describe("RoadTracker", () => {
  it("describes the progress for screen readers", () => {
    render(<RoadTracker status="IN_PROGRESS" />);
    expect(screen.getByRole("img", { name: /Being fixed. A worker is on it/ })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });
  it("RESOLVED marks every stop as done", () => {
    const { container } = render(<RoadTracker status="RESOLVED" />);
    expect(container.querySelectorAll("li .bg-highway")).toHaveLength(3);
    expect(container.querySelector(".bg-signal")).toBeNull();
  });
  it("SUBMITTED has the current stop at the start, nothing done", () => {
    const { container } = render(<RoadTracker status="SUBMITTED" />);
    expect(container.querySelectorAll("li .bg-highway")).toHaveLength(0);
    expect(container.querySelectorAll("li .bg-signal")).toHaveLength(1);
  });
});

describe("StatusPill", () => {
  it("shows Overdue only while unresolved", () => {
    const { rerender } = render(<StatusPill status="IN_PROGRESS" overdue />);
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    rerender(<StatusPill status="RESOLVED" overdue />);
    expect(screen.queryByText("Overdue")).toBeNull();
  });
});

describe("ComplaintCard", () => {
  const c = { id: "abc", title: "Pothole on MG Road", complaintNumber: "CIV-1", status: "SUBMITTED", overdue: false, upvoteCount: 1, createdAt: "2026-10-10T10:00:00Z", category: { name: "Roads" }, photoUrl: "/uploads/a.jpg" };
  it("links to the detail page and shows key facts", () => {
    render(<ComplaintCard complaint={c} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/citizen/complaints/abc");
    expect(screen.getByText("Pothole on MG Road")).toBeInTheDocument();
    expect(screen.getByText("1 upvote")).toBeInTheDocument();
    expect(screen.getByText(/Roads on/)).toBeInTheDocument();
  });
});

describe("UpvoteButton", () => {
  function stub(sequence) {
    const queue = [...sequence];
    vi.stubGlobal("fetch", vi.fn(async () => {
      const [status, body] = queue.shift();
      return { ok: status < 400, status, json: async () => body };
    }));
  }
  it("upvotes then removes the upvote, updating the count", async () => {
    stub([[201, { success: true, data: { upvoteCount: 4, hasUpvoted: true } }], [200, { success: true, data: { upvoteCount: 3, hasUpvoted: false } }]]);
    render(<UpvoteButton complaintId="x" initialCount={3} initialUpvoted={false} />);
    const btn = screen.getByRole("button", { name: /Upvote/ });
    expect(btn).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(btn);
    await waitFor(() => expect(screen.getByRole("button", { name: /Upvoted/ })).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByText("4 people")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button"));
    await waitFor(() => expect(screen.getByText("3 people")).toBeInTheDocument());
    expect(fetch.mock.calls.map((c) => c[1].method)).toEqual(["POST", "DELETE"]);
  });
  it("shows the server's message and keeps the old state when it fails", async () => {
    stub([[409, { success: false, message: "You cannot upvote your own complaint" }]]);
    render(<UpvoteButton complaintId="x" initialCount={0} initialUpvoted={false} />);
    await userEvent.click(screen.getByRole("button"));
    expect(await screen.findByText("You cannot upvote your own complaint")).toBeInTheDocument();
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "false");
  });
});

describe("BadgeStamp", () => {
  it("shows emoji icons, otherwise a generic medal; locked badges show the points needed", () => {
    const { rerender } = render(<BadgeStamp badge={{ name: "Starter", icon: "🌱", pointsRequired: 10 }} />);
    expect(screen.getByText("🌱")).toBeInTheDocument();
    expect(screen.getByText("Earned")).toBeInTheDocument();
    rerender(<BadgeStamp badge={{ name: "Hero", icon: "some-long-icon-name", pointsRequired: 100 }} earned={false} />);
    expect(screen.queryByText("some-long-icon-name")).toBeNull();
    expect(screen.getByText("100 points")).toBeInTheDocument();
  });
});
