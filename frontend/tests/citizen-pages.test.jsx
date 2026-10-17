import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/citizen",
  useParams: () => ({ id: "c1" }),
}));
// The real map needs a browser; stand in with a button that "clicks" a point and lists pins.
vi.mock("@/components/MapViewLoader", () => ({
  default: ({ markers = [], onPick, center }) => (
    <div>
      {onPick && <button onClick={() => onPick({ lat: 19.1, lng: 72.9 })}>click-map</button>}
      <span data-testid="map-center">{center.lat},{center.lng}</span>
      <span data-testid="pin-count">{markers.length}</span>
    </div>
  ),
}));

import { AuthProvider } from "@/context/AuthContext";
import CitizenHome from "@/app/citizen/page";
import MyComplaintsPage from "@/app/citizen/complaints/page";
import ComplaintDetailPage from "@/app/citizen/complaints/[id]/page";
import NearbyPage from "@/app/citizen/nearby/page";
import NotificationsPage from "@/app/citizen/notifications/page";
import RewardsPage from "@/app/citizen/rewards/page";

const USER = { id: "u1", name: "Tina Rao", email: "t@e.co", role: "CITIZEN", points: 12 };
const ok = (data) => [200, { success: true, data }];
let calls;

function backend(routes) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn(async (url, opts = {}) => {
    const u = new URL(url);
    const path = u.pathname.replace("/api/v1", "");
    const method = opts.method || "GET";
    calls.push({ method, path, query: Object.fromEntries(u.searchParams) });
    const key = `${method} ${path}`;
    const handler = routes[key] ?? (key === "GET /auth/me" ? ok(USER) : null);
    if (!handler) throw new Error("unmocked " + key);
    const [status, body] = typeof handler === "function" ? handler(Object.fromEntries(u.searchParams)) : handler;
    return { ok: status < 400, status, json: async () => body };
  }));
}
const wrap = (ui) => render(<AuthProvider>{ui}</AuthProvider>);
const complaint = (n, over = {}) => ({
  id: `c${n}`, title: `Complaint ${n}`, complaintNumber: `CIV-${n}`, status: "SUBMITTED", overdue: false,
  upvoteCount: 0, createdAt: "2026-10-10T10:00:00Z", category: { name: "Roads" }, department: { name: "Roads dept" },
  photoUrl: `/uploads/${n}.jpg`, location: { type: "Point", coordinates: [72.87, 19.07] }, description: "A long enough description", ...over,
});

beforeEach(() => window.localStorage.setItem("civic_access_token", "T"));

describe("citizen home", () => {
  it("greets by first name, shows points progress and latest complaints", async () => {
    backend({
      "GET /gamification/me": ok({ points: 12, badges: [], nextBadge: { name: "Active Citizen", pointsRequired: 50, pointsNeeded: 38 }, recentActivity: [] }),
      "GET /complaints": ok({ items: [complaint(1), complaint(2)], total: 2, page: 1, limit: 3 }),
    });
    wrap(<CitizenHome />);
    expect(await screen.findByText("Complaint 1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Hello, Tina/ })).toBeInTheDocument();
    expect(await screen.findByText("38 more points to earn the Active Citizen badge.")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "24");
    expect(calls.find((c) => c.path === "/complaints").query.limit).toBe("3");
  });

  it("empty state invites the first report", async () => {
    backend({
      "GET /gamification/me": ok({ points: 0, badges: [], nextBadge: null, recentActivity: [] }),
      "GET /complaints": ok({ items: [], total: 0, page: 1, limit: 3 }),
    });
    wrap(<CitizenHome />);
    expect(await screen.findByText("You have not reported anything yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Report your first issue" })).toHaveAttribute("href", "/citizen/report");
  });

  it("shows an error message instead of crashing", async () => {
    backend({
      "GET /gamification/me": [500, { success: false, message: "Internal server error" }],
      "GET /complaints": [500, { success: false, message: "Internal server error" }],
    });
    wrap(<CitizenHome />);
    expect((await screen.findAllByText("Internal server error")).length).toBeGreaterThan(0);
  });
});

describe("my complaints", () => {
  it("filters by progress, and shows more pages", async () => {
    backend({
      "GET /complaints": ({ status, page }) => {
        if (status === "RESOLVED") return ok({ items: [], total: 0, page: 1, limit: 10 });
        const all = Array.from({ length: 12 }, (_, i) => complaint(i + 1));
        return ok({ items: page === "2" ? all.slice(10) : all.slice(0, 10), total: 12, page: Number(page), limit: 10 });
      },
    });
    const user = userEvent.setup();
    wrap(<MyComplaintsPage />);
    expect(await screen.findByText("Complaint 1")).toBeInTheDocument();
    expect(screen.getByText("Showing 10 of 12")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show more" }));
    expect(await screen.findByText("Complaint 12")).toBeInTheDocument();
    expect(screen.getByText("Showing 12 of 12")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Resolved" }));
    expect(await screen.findByText(/Nothing is "resolved" right now/)).toBeInTheDocument();
    expect(calls.at(-1).query.status).toBe("RESOLVED");
    expect(calls.at(-1).query.page).toBe("1");
  });
});

describe("complaint detail", () => {
  it("shows progress, description and details", async () => {
    backend({ "GET /complaints/c1": ok(complaint(1, { status: "IN_PROGRESS", overdue: true, upvoteCount: 2 })) });
    wrap(<ComplaintDetailPage />);
    expect(await screen.findByRole("heading", { name: "Complaint 1" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Being fixed/ })).toBeInTheDocument();
    expect(screen.getByText(/taking longer than expected/)).toBeInTheDocument();
    expect(screen.getByText("Roads dept")).toBeInTheDocument();
    expect(screen.getByText("2 upvotes")).toBeInTheDocument();
    expect(screen.getByTestId("pin-count")).toHaveTextContent("1");
  });
  it("someone else's complaint gets a friendly 404 message", async () => {
    backend({ "GET /complaints/c1": [404, { success: false, message: "Complaint not found" }] });
    wrap(<ComplaintDetailPage />);
    expect(await screen.findByText(/could not find this complaint/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to my complaints" })).toBeInTheDocument();
  });
});

describe("nearby", () => {
  const nearby = ok({ count: 2, radiusMeters: 500, items: [
    complaint(1, { isOwnComplaint: true, distanceMeters: 20, reporter: { name: "Tina Rao" }, hasUpvoted: false }),
    complaint(2, { isOwnComplaint: false, distanceMeters: 150, reporter: null, hasUpvoted: false, upvoteCount: 3 }),
  ] });
  it("waits for a location, then lists nearby complaints with upvote only on others'", async () => {
    backend({ "GET /categories": ok([{ id: "k1", name: "Roads" }]), "GET /complaints/nearby": nearby });
    const user = userEvent.setup();
    wrap(<NearbyPage />);
    expect(await screen.findByTestId("nearby-hint")).toHaveTextContent("Use your location");
    expect(calls.some((c) => c.path === "/complaints/nearby")).toBe(false);
    await user.click(screen.getByText("click-map"));
    expect(await screen.findByText("2 complaints nearby")).toBeInTheDocument();
    const q = calls.find((c) => c.path === "/complaints/nearby").query;
    expect(q.latitude).toBe("19.1");
    expect(q.longitude).toBe("72.9");
    expect(q.radius).toBe("500");
    expect(screen.getByText("Your complaint")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Upvote/ })).toHaveLength(1);
    expect(screen.getByTestId("pin-count")).toHaveTextContent("2");
    await user.selectOptions(screen.getByLabelText("Distance"), "1000");
    await waitFor(() => expect(calls.at(-1).query.radius).toBe("1000"));
  });
  it("empty area invites the citizen to report", async () => {
    backend({ "GET /categories": ok([]), "GET /complaints/nearby": ok({ count: 0, radiusMeters: 500, items: [] }) });
    const user = userEvent.setup();
    wrap(<NearbyPage />);
    await user.click(await screen.findByText("click-map"));
    expect(await screen.findByText("Nothing reported here yet")).toBeInTheDocument();
  });
});

describe("notifications", () => {
  it("marks one as read when opened, and all as read", async () => {
    let unread = 2;
    backend({
      "GET /notifications": () => ok({ items: [
        { id: "n1", type: "STATUS_CHANGED", title: "Status changed", message: "Now being fixed", complaintId: "c1", isRead: false, createdAt: "2026-10-10T10:00:00Z" },
        { id: "n2", type: "BADGE_EARNED", title: "New badge", message: "Starter", complaintId: null, isRead: false, createdAt: "2026-10-10T10:00:00Z" },
      ], total: 2, unreadCount: unread }),
      "PATCH /notifications/read-all": () => { unread = 0; return ok({ modified: 2 }); },
      "PATCH /notifications/n1/read": ok({}),
    });
    const user = userEvent.setup();
    wrap(<NotificationsPage />);
    expect(await screen.findByText("Status changed")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Unread")).toHaveLength(2);
    expect(screen.getByRole("link", { name: /Status changed/ })).toHaveAttribute("href", "/citizen/complaints/c1");
    await user.click(screen.getByRole("link", { name: /Status changed/ }));
    expect(calls.some((c) => c.method === "PATCH" && c.path === "/notifications/n1/read")).toBe(true);
    await user.click(screen.getByRole("button", { name: "Mark all as read" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Mark all as read" })).toBeNull());
  });
  it("empty state explains when alerts appear", async () => {
    backend({ "GET /notifications": ok({ items: [], total: 0, unreadCount: 0 }) });
    wrap(<NotificationsPage />);
    expect(await screen.findByText("No alerts yet")).toBeInTheDocument();
  });
});

describe("rewards", () => {
  it("shows points, earned vs locked badges, activity and leaderboard", async () => {
    backend({
      "GET /gamification/me": ok({ points: 60, badges: [{ name: "Starter", description: "", icon: "🌱", pointsRequired: 10 }], nextBadge: { name: "Hero", pointsRequired: 100, pointsNeeded: 40 },
        recentActivity: [{ event: "COMPLAINT_CREATED", points: 10, complaintId: "c1", createdAt: "2026-10-10T10:00:00Z" }] }),
      "GET /gamification/badges": ok([{ name: "Starter", icon: "🌱", pointsRequired: 10 }, { name: "Hero", icon: "x", pointsRequired: 100 }]),
      "GET /gamification/leaderboard": ok([{ rank: 1, name: "Tina Rao", points: 60, badgeCount: 1 }, { rank: 2, name: "Bob", points: 30, badgeCount: 0 }]),
    });
    wrap(<RewardsPage />);
    expect(await screen.findByTestId("rewards-points")).toHaveTextContent("60");
    expect(screen.getByText("Earned")).toBeInTheDocument();
    expect(screen.getByText("100 points")).toBeInTheDocument();
    expect(screen.getByText("You reported an issue")).toBeInTheDocument();
    expect(screen.getByText("+10")).toBeInTheDocument();
    const board = screen.getByRole("region", { name: "Leaderboard" });
    expect(within(board).getByText("Bob")).toBeInTheDocument();
  });
});

describe("top bar bell", () => {
  it("clears its unread count right after 'Mark all as read' (no page change needed)", async () => {
    let unread = 3;
    backend({
      "GET /notifications": () => ok({ items: [{ id: "n1", type: "STATUS_CHANGED", title: "Status changed", message: "m", complaintId: null, isRead: unread === 0, createdAt: "2026-10-10T10:00:00Z" }], total: 1, unreadCount: unread }),
      "PATCH /notifications/read-all": () => { unread = 0; return ok({ modified: 3 }); },
    });
    const { default: Navbar } = await import("@/components/Navbar");
    const user = userEvent.setup();
    wrap(<><Navbar /><NotificationsPage /></>);
    expect(await screen.findByTestId("unread-count")).toHaveTextContent("3");
    await user.click(await screen.findByRole("button", { name: "Mark all as read" }));
    await waitFor(() => expect(screen.queryByTestId("unread-count")).toBeNull());
  });
});
