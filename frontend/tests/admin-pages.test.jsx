import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

let search = "";
vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/admin",
  useParams: () => ({ id: "c1" }),
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("@/components/MapViewLoader", () => ({
  default: ({ markers = [], center, zoom }) => (
    <div>
      <span data-testid="map-center">{center.lat.toFixed(3)},{center.lng.toFixed(3)}</span>
      <span data-testid="map-zoom">{zoom}</span>
      <span data-testid="pin-count">{markers.length}</span>
    </div>
  ),
}));

import { AuthProvider } from "@/context/AuthContext";
import AdminDashboard from "@/app/admin/page";
import AdminComplaintsPage from "@/app/admin/complaints/page";
import AdminComplaintDetail from "@/app/admin/complaints/[id]/page";
import AdminMapPage from "@/app/admin/map/page";
import OverduePage from "@/app/admin/overdue/page";
import { foldTail, share, compact, fitView } from "@/lib/charts";

const ADMIN = { id: "a1", name: "Sana Admin", email: "a@e.co", role: "ADMIN" };
const ok = (data) => [200, { success: true, data }];
let calls;

function backend(routes) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn(async (url, opts = {}) => {
    const u = new URL(url);
    const path = u.pathname.replace("/api/v1", "");
    const method = opts.method || "GET";
    const query = Object.fromEntries(u.searchParams);
    calls.push({ method, path, query, body: opts.body });
    const key = `${method} ${path}`;
    const handler = routes[key] ?? (key === "GET /auth/me" ? ok(ADMIN) : null);
    if (!handler) throw new Error("unmocked " + key);
    const [status, body] = typeof handler === "function" ? handler(query, opts) : handler;
    return { ok: status < 400, status, json: async () => body };
  }));
}
const wrap = (ui) => render(<AuthProvider>{ui}</AuthProvider>);
const item = (n, over = {}) => ({
  id: `c${n}`, title: `Complaint ${n}`, complaintNumber: `CIV-${n}`, status: "SUBMITTED", overdue: false, upvoteCount: 1,
  category: { name: "Pothole" }, department: { name: "Road" }, createdAt: new Date().toISOString(), photoUrl: "/uploads/a.jpg",
  assignedWorker: null, ...over,
});
const dashboard = (over = {}) => ({
  totals: { total: 10, submitted: 4, inProgress: 3, resolved: 3, overdue: 2 },
  resolutionRatePercent: 30,
  byStatus: [{ status: "SUBMITTED", count: 4 }, { status: "IN_PROGRESS", count: 3 }, { status: "RESOLVED", count: 3 }],
  byCategory: [{ id: "k1", name: "Pothole", count: 6 }, { id: "k2", name: "Garbage", count: 4 }],
  byDepartment: [{ id: "d1", name: "Road", count: 6 }, { id: "d2", name: "Sanitation", count: 4 }],
  recentComplaints: [item(1), item(2)],
  oldestOverdue: [item(3, { ageDays: 9, overdue: true })],
  ...over,
});

beforeEach(() => {
  search = "";
  window.localStorage.setItem("civic_access_token", "T");
});

describe("chart helpers", () => {
  it("folds the tail of a long list into Other", () => {
    const rows = Array.from({ length: 11 }, (_, i) => ({ id: `r${i}`, name: `N${i}`, count: 11 - i }));
    const folded = foldTail(rows, 8);
    expect(folded).toHaveLength(8);
    expect(folded.at(-1)).toEqual({ id: "other", name: "Other", count: 4 + 3 + 2 + 1 });
    expect(foldTail(rows.slice(0, 8), 8)).toHaveLength(8);
  });
  it("works out shares, compact numbers and a map view", () => {
    expect(share(1, 3)).toBe(33.3);
    expect(share(0, 0)).toBe(0);
    expect(compact(950)).toBe("950");
    expect(compact(12900)).toBe("12.9K");
    expect(compact(2_000_000)).toBe("2M");
    expect(fitView([]).zoom).toBe(5);
    expect(fitView([{ lat: 19.1, lng: 73.1 }]).zoom).toBe(16);
    expect(fitView([{ lat: 19.1, lng: 73.1 }, { lat: 19.12, lng: 73.1 }]).zoom).toBe(14);
    expect(fitView([{ lat: 19.1, lng: 73.1 }, { lat: 19.4, lng: 73.1 }]).zoom).toBe(10);
    const wide = fitView([{ lat: 10, lng: 70 }, { lat: 28, lng: 78 }]);
    expect(wide.zoom).toBe(5);
    expect(wide.center).toEqual({ lat: 19, lng: 74 });
  });
});

describe("admin dashboard", () => {
  it("shows the rate, tiles that link to filtered lists, and the charts", async () => {
    backend({ "GET /admin/dashboard": ok(dashboard()) });
    wrap(<AdminDashboard />);
    expect(await screen.findByTestId("resolution-rate")).toHaveTextContent("30%");
    expect(screen.getByTestId("stat-total")).toHaveTextContent("10");
    expect(screen.getByTestId("stat-overdue")).toHaveTextContent("2");
    expect(screen.getByTestId("stat-submitted").closest("a")).toHaveAttribute("href", "/admin/complaints?status=SUBMITTED");
    expect(screen.getByTestId("stat-inProgress").closest("a")).toHaveAttribute("href", "/admin/complaints?status=IN_PROGRESS");
    expect(screen.getByTestId("stat-overdue").closest("a")).toHaveAttribute("href", "/admin/overdue");
    // chart rows carry their numbers for screen readers
    expect(screen.getByLabelText("Pothole: 6 complaints, 60% of all")).toBeInTheDocument();
    expect(screen.getByLabelText("Sanitation: 4 complaints, 40% of all")).toBeInTheDocument();
    // status bar legend always names every status
    expect(screen.getByRole("img", { name: "Reported: 4, Being fixed: 3, Resolved: 3" })).toBeInTheDocument();
    expect(screen.getByText("Complaint 3")).toBeInTheDocument();
    expect(screen.getByText("9 days old")).toBeInTheDocument();
    expect(screen.getByText("Complaint 1").closest("a")).toHaveAttribute("href", "/admin/complaints/c1");
  });

  it("draws each bar in proportion to its count, longest bar full width", async () => {
    backend({ "GET /admin/dashboard": ok(dashboard()) });
    wrap(<AdminDashboard />);
    await screen.findByTestId("resolution-rate");
    const category = screen.getByRole("region", { name: "By category" });
    const bars = within(category).getAllByTestId("bar");
    expect(bars[0]).toHaveStyle({ width: "100%" }); // Pothole 6 of max 6
    expect(parseFloat(bars[1].style.width)).toBeCloseTo(66.67, 1); // Garbage 4 of max 6
  });

  it("every chart has a table view with the same numbers", async () => {
    backend({ "GET /admin/dashboard": ok(dashboard()) });
    wrap(<AdminDashboard />);
    await screen.findByTestId("resolution-rate");
    const sections = screen.getAllByText("Show as table");
    expect(sections).toHaveLength(2);
    const category = screen.getByRole("region", { name: "By category" });
    expect(within(category).getByRole("cell", { name: "Garbage" })).toBeInTheDocument();
    expect(within(category).getByRole("cell", { name: "40%" })).toBeInTheDocument();
  });

  it("folds a long category list so the chart never needs more colours", async () => {
    const many = Array.from({ length: 12 }, (_, i) => ({ id: `k${i}`, name: `Cat ${i}`, count: 12 - i }));
    backend({ "GET /admin/dashboard": ok(dashboard({ byCategory: many })) });
    wrap(<AdminDashboard />);
    await screen.findByTestId("resolution-rate");
    const category = screen.getByRole("region", { name: "By category" });
    expect(within(category).getAllByRole("listitem")).toHaveLength(8);
    expect(within(category).getAllByText("Other").length).toBeGreaterThan(0);
  });

  it("copes with an empty system", async () => {
    backend({
      "GET /admin/dashboard": ok(dashboard({
        totals: { total: 0, submitted: 0, inProgress: 0, resolved: 0, overdue: 0 }, resolutionRatePercent: 0,
        byStatus: [{ status: "SUBMITTED", count: 0 }, { status: "IN_PROGRESS", count: 0 }, { status: "RESOLVED", count: 0 }],
        byCategory: [], byDepartment: [], recentComplaints: [], oldestOverdue: [],
      })),
    });
    wrap(<AdminDashboard />);
    expect(await screen.findByText("No complaints yet.")).toBeInTheDocument();
    expect(screen.getByText("Nothing is overdue")).toBeInTheDocument();
    expect(screen.getAllByText("Nothing to show yet.")).toHaveLength(2);
  });

  it("runs the overdue check and reports the result", async () => {
    backend({
      "GET /admin/dashboard": ok(dashboard()),
      "POST /admin/overdue/check": ok({ checked: 7, markedOverdue: 2 }),
    });
    const user = userEvent.setup();
    wrap(<AdminDashboard />);
    await user.click(await screen.findByRole("button", { name: "Run overdue check now" }));
    expect(await screen.findByText("Checked 7 open complaints. 2 newly marked overdue.")).toBeInTheDocument();
    expect(calls.filter((c) => c.path === "/admin/dashboard")).toHaveLength(2); // refreshed afterwards
  });

  it("shows a server error", async () => {
    backend({ "GET /admin/dashboard": [500, { success: false, message: "Something went wrong", errors: [] }] });
    wrap(<AdminDashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
  });
});

describe("admin complaints list", () => {
  const lists = {
    "GET /admin/departments": ok([{ id: "d1", name: "Road" }, { id: "d2", name: "Sanitation" }]),
    "GET /admin/categories": ok([{ id: "k1", name: "Pothole" }]),
  };

  it("opens on the filter from the link and sends the right query", async () => {
    search = "status=IN_PROGRESS&overdue=true";
    backend({ ...lists, "GET /admin/complaints": ok({ items: [item(1, { status: "IN_PROGRESS" })], total: 1, page: 1, limit: 20 }) });
    wrap(<AdminComplaintsPage />);
    expect(await screen.findByText("Complaint 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Progress")).toHaveValue("IN_PROGRESS");
    expect(screen.getByLabelText("Only overdue")).toBeChecked();
    expect(calls.find((c) => c.path === "/admin/complaints").query).toMatchObject({ status: "IN_PROGRESS", overdue: "true", page: "1", limit: "20" });
    expect(screen.getByTestId("result-count")).toHaveTextContent("1 complaint");
  });

  it("filters by department, category and number, and can clear them", async () => {
    backend({ ...lists, "GET /admin/complaints": ok({ items: [item(1)], total: 1, page: 1, limit: 20 }) });
    const user = userEvent.setup();
    wrap(<AdminComplaintsPage />);
    await screen.findByText("Complaint 1");
    await screen.findByRole("option", { name: "Sanitation" });
    await user.selectOptions(screen.getByLabelText("Department"), "d2");
    await waitFor(() => expect(calls.at(-1).query.departmentId).toBe("d2"));
    await user.selectOptions(screen.getByLabelText("Category"), "k1");
    await waitFor(() => expect(calls.at(-1).query.categoryId).toBe("k1"));
    await user.type(screen.getByLabelText("Complaint number"), " civ-2026-000001 ");
    await user.click(screen.getByRole("button", { name: "Find" }));
    await waitFor(() => expect(calls.at(-1).query.number).toBe("civ-2026-000001"));
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await waitFor(() => expect(calls.at(-1).query.departmentId).toBeUndefined());
    expect(screen.getByLabelText("Department")).toHaveValue("");
    expect(screen.getByLabelText("Complaint number")).toHaveValue("");
  });

  it("pages through the results and starts at page 1 after a filter change", async () => {
    backend({
      ...lists,
      "GET /admin/complaints": (q) => ok({ items: [item(Number(q.page) * 10)], total: 45, page: Number(q.page), limit: 20 }),
    });
    const user = userEvent.setup();
    wrap(<AdminComplaintsPage />);
    expect(await screen.findByText("Complaint 10")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 3 (45 in all)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Complaint 20")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Complaint 30")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Progress"), "RESOLVED");
    expect(await screen.findByText("Page 1 of 3 (45 in all)")).toBeInTheDocument();
    expect(calls.at(-1).query).toMatchObject({ status: "RESOLVED", page: "1" });
  });

  it("explains an empty result", async () => {
    backend({ ...lists, "GET /admin/complaints": ok({ items: [], total: 0, page: 1, limit: 20 }) });
    wrap(<AdminComplaintsPage />);
    expect(await screen.findByText("No complaints match these filters")).toBeInTheDocument();
  });
});

describe("admin complaint detail", () => {
  const detail = (over = {}) => ({
    ...item(1), description: "Deep pothole near the bus stop", location: { type: "Point", coordinates: [73.192, 19.1867] },
    reporter: { id: "u1", name: "Tina" }, photoGeotagged: true, resolutionPhotoUrl: null, resolvedAt: null,
    priority: "MEDIUM", allowedNextStatuses: ["IN_PROGRESS"], ...over,
  });

  it("moves a complaint to the next status with a note", async () => {
    let current = detail();
    backend({
      "GET /admin/complaints/c1": () => ok(current),
      "PATCH /complaints/c1/status": (q, opts) => {
        current = detail({ status: "IN_PROGRESS", allowedNextStatuses: ["RESOLVED"] });
        return ok({});
      },
    });
    const user = userEvent.setup();
    wrap(<AdminComplaintDetail />);
    expect(await screen.findByRole("heading", { name: "Complaint 1" })).toBeInTheDocument();
    expect(screen.getByTestId("geotag-badge")).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Note for the citizen/), "Crew assigned");
    await user.click(screen.getByRole("button", { name: "Mark as being fixed" }));
    expect(await screen.findByRole("button", { name: "Mark as resolved" })).toBeInTheDocument();
    expect(screen.getByText(/resolve without an after-fix photo/)).toBeInTheDocument();
    const patch = calls.find((c) => c.method === "PATCH");
    expect(JSON.parse(patch.body)).toEqual({ status: "IN_PROGRESS", note: "Crew assigned" });
  });

  it("sends no note field when the note is empty", async () => {
    backend({ "GET /admin/complaints/c1": ok(detail()), "PATCH /complaints/c1/status": ok({}) });
    const user = userEvent.setup();
    wrap(<AdminComplaintDetail />);
    await user.click(await screen.findByRole("button", { name: "Mark as being fixed" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PATCH")).toBe(true));
    expect(JSON.parse(calls.find((c) => c.method === "PATCH").body)).toEqual({ status: "IN_PROGRESS" });
  });

  it("shows a resolved complaint with its after-fix photo and no status control", async () => {
    backend({ "GET /admin/complaints/c1": ok(detail({ status: "RESOLVED", allowedNextStatuses: [], resolutionPhotoUrl: "/uploads/resolutions/x.jpg", resolvedAt: new Date().toISOString(), assignedWorker: { id: "w", name: "Ravi" } })) });
    wrap(<AdminComplaintDetail />);
    expect(await screen.findByText(/status can no longer change/)).toBeInTheDocument();
    expect(screen.getByAltText("After-fix photo")).toBeInTheDocument();
    expect(screen.getByText("Ravi")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Mark as/ })).toBeNull();
  });

  it("shows the server's message when the status change is refused", async () => {
    backend({
      "GET /admin/complaints/c1": ok(detail()),
      "PATCH /complaints/c1/status": [409, { success: false, message: "This complaint was just updated by someone else. Please refresh and try again", errors: [] }],
    });
    const user = userEvent.setup();
    wrap(<AdminComplaintDetail />);
    await user.click(await screen.findByRole("button", { name: "Mark as being fixed" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("just updated by someone else");
  });

  it("saves a new priority only when it changed", async () => {
    backend({ "GET /admin/complaints/c1": ok(detail()), "PATCH /complaints/c1": ok({}) });
    const user = userEvent.setup();
    wrap(<AdminComplaintDetail />);
    const save = await screen.findByRole("button", { name: "Save priority" });
    expect(save).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Priority"), "HIGH");
    expect(save).toBeEnabled();
    await user.click(save);
    expect(await screen.findByText("Priority saved.")).toBeInTheDocument();
    expect(JSON.parse(calls.find((c) => c.method === "PATCH" && c.path === "/complaints/c1").body)).toEqual({ priority: "HIGH" });
  });

  it("names an anonymous reporter Anonymous and explains a missing complaint", async () => {
    backend({ "GET /admin/complaints/c1": ok(detail({ reporter: null })) });
    const first = wrap(<AdminComplaintDetail />);
    expect(await screen.findByText("Anonymous")).toBeInTheDocument();
    first.unmount();
    backend({ "GET /admin/complaints/c1": [404, { success: false, message: "Complaint not found", errors: [] }] });
    wrap(<AdminComplaintDetail />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Complaint not found");
  });
});

describe("admin map", () => {
  const pin = (n, status, lat, lng) => ({ id: `c${n}`, complaintNumber: `CIV-${n}`, title: `T${n}`, status, latitude: lat, longitude: lng });

  it("draws every pin, counts them per status and fits the view", async () => {
    backend({
      "GET /admin/complaints/map": ok({ items: [pin(1, "SUBMITTED", 19.1, 73.1), pin(2, "SUBMITTED", 19.101, 73.101), pin(3, "RESOLVED", 19.102, 73.1)], count: 3, limit: 500 }),
    });
    wrap(<AdminMapPage />);
    expect(await screen.findByTestId("pin-count")).toHaveTextContent("3");
    expect(screen.getByTestId("pins-SUBMITTED")).toHaveTextContent("2");
    expect(screen.getByTestId("pins-IN_PROGRESS")).toHaveTextContent("0");
    expect(screen.getByTestId("pins-RESOLVED")).toHaveTextContent("1");
    expect(screen.getByTestId("map-zoom")).toHaveTextContent("16"); // pins only 200 m apart
  });

  it("filters by status and overdue", async () => {
    backend({ "GET /admin/complaints/map": ok({ items: [], count: 0, limit: 500 }) });
    const user = userEvent.setup();
    wrap(<AdminMapPage />);
    expect(await screen.findByText("No complaints match these filters.")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Progress"), "IN_PROGRESS");
    await waitFor(() => expect(calls.at(-1).query.status).toBe("IN_PROGRESS"));
    await user.click(screen.getByLabelText("Only overdue"));
    await waitFor(() => expect(calls.at(-1).query.overdue).toBe("true"));
  });

  it("warns when the map is showing only the newest complaints", async () => {
    backend({ "GET /admin/complaints/map": ok({ items: [pin(1, "SUBMITTED", 19, 73)], count: 500, limit: 500 }) });
    wrap(<AdminMapPage />);
    expect(await screen.findByText(/Showing the newest 500 complaints/)).toBeInTheDocument();
  });
});

describe("overdue page", () => {
  it("lists the oldest first with their age and can run the check", async () => {
    backend({
      "GET /admin/overdue": ok({ items: [item(1, { ageDays: 12, overdue: true }), item(2, { ageDays: 1, overdue: true })], total: 2, page: 1, limit: 20 }),
      "POST /admin/overdue/check": ok({ checked: 5, markedOverdue: 0 }),
    });
    const user = userEvent.setup();
    wrap(<OverduePage />);
    expect(await screen.findByText("12 days old")).toBeInTheDocument();
    expect(screen.getByText("1 day old")).toBeInTheDocument();
    expect(screen.getByTestId("overdue-count")).toHaveTextContent("2 overdue");
    await user.click(screen.getByRole("button", { name: "Run overdue check now" }));
    expect(await screen.findByText("Checked 5 open complaints. 0 newly marked overdue.")).toBeInTheDocument();
  });

  it("says so when nothing is overdue", async () => {
    backend({ "GET /admin/overdue": ok({ items: [], total: 0, page: 1, limit: 20 }) });
    wrap(<OverduePage />);
    expect(await screen.findByText("Nothing is overdue")).toBeInTheDocument();
  });

  it("shows a failed check as an error", async () => {
    backend({
      "GET /admin/overdue": ok({ items: [], total: 0, page: 1, limit: 20 }),
      "POST /admin/overdue/check": [500, { success: false, message: "Overdue check failed", errors: [] }],
    });
    const user = userEvent.setup();
    wrap(<OverduePage />);
    await user.click(await screen.findByRole("button", { name: "Run overdue check now" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Overdue check failed");
  });
});
