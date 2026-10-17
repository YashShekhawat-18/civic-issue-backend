import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

let search = "";
vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/worker",
  useParams: () => ({ id: "c1" }),
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("@/components/MapViewLoader", () => ({
  default: ({ center }) => <span data-testid="map-center">{center.lat},{center.lng}</span>,
}));

import { AuthProvider } from "@/context/AuthContext";
import WorkerHome from "@/app/worker/page";
import TasksPage from "@/app/worker/tasks/page";
import TaskDetailPage from "@/app/worker/tasks/[id]/page";
import { gpsPhoto, noGpsPhoto, southWestPhoto } from "./photos";

const WORKER = { id: "w1", name: "Ravi Kumar", email: "r@e.co", role: "WORKER" };
const ok = (data) => [200, { success: true, data }];
let calls;

function backend(routes) {
  calls = [];
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: () => "blob:x", revokeObjectURL: () => {} }));
  vi.stubGlobal("fetch", vi.fn(async (url, opts = {}) => {
    const u = new URL(url);
    const path = u.pathname.replace("/api/v1", "");
    const method = opts.method || "GET";
    const query = Object.fromEntries(u.searchParams);
    calls.push({ method, path, query, body: opts.body });
    const key = `${method} ${path}`;
    const handler = routes[key] ?? (key === "GET /auth/me" ? ok(WORKER) : null);
    if (!handler) throw new Error("unmocked " + key);
    const [status, body] = typeof handler === "function" ? handler(query, opts) : handler;
    return { ok: status < 400, status, json: async () => body };
  }));
}
const wrap = (ui) => render(<AuthProvider>{ui}</AuthProvider>);
const task = (n, over = {}) => ({
  id: `c${n}`, title: `Task ${n}`, complaintNumber: `CIV-${n}`, status: "SUBMITTED", overdue: false, upvoteCount: 2,
  category: { name: "Pothole" }, createdAt: new Date().toISOString(), photoUrl: "/uploads/a.jpg", assignedWorker: null, ...over,
});
const detail = (over = {}) => ({
  ...task(1), description: "Deep pothole near the bus stop", location: { type: "Point", coordinates: [73.192, 19.1867] },
  reporter: { name: "Tina" }, photoGeotagged: true, resolutionPhotoUrl: null, resolvedAt: null, ...over,
});

beforeEach(() => {
  search = "";
  window.localStorage.setItem("civic_access_token", "T");
});

describe("worker dashboard", () => {
  it("shows the three counts and the short lists, asking the backend the right questions", async () => {
    backend({
      "GET /worker/complaints": (q) => {
        if (q.limit === "1") return ok({ items: [], total: q.overdue ? 1 : q.assignedToMe ? 2 : 7 });
        return ok({ items: q.assignedToMe ? [task(1, { status: "IN_PROGRESS" })] : [task(2), task(3)], total: 9 });
      },
    });
    wrap(<WorkerHome />);
    expect(await screen.findByText("Hello, Ravi")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("tile-new")).toHaveTextContent("7"));
    expect(screen.getByTestId("tile-mine")).toHaveTextContent("2");
    expect(screen.getByTestId("tile-overdue")).toHaveTextContent("1");
    expect(await screen.findByText("Task 2")).toBeInTheDocument();
    expect(screen.getByText("Task 1")).toBeInTheDocument();
    const asked = calls.filter((c) => c.path === "/worker/complaints").map((c) => c.query);
    expect(asked).toContainEqual({ status: "SUBMITTED", limit: "1" });
    expect(asked).toContainEqual({ status: "IN_PROGRESS", assignedToMe: "true", limit: "1" });
    expect(asked).toContainEqual({ overdue: "true", limit: "1" });
    expect(asked.some((q) => "key" in q || "id" in q)).toBe(false);
  });

  it("explains empty lists", async () => {
    backend({ "GET /worker/complaints": ok({ items: [], total: 0 }) });
    wrap(<WorkerHome />);
    expect(await screen.findByText("You have no jobs in progress")).toBeInTheDocument();
    expect(screen.getByText("No new reports")).toBeInTheDocument();
  });
});

describe("tasks list", () => {
  it("opens on the filter chosen in the link and switches filters", async () => {
    search = "filter=mine";
    backend({ "GET /worker/complaints": (q) => ok({ items: [task(q.status === "RESOLVED" ? 8 : 5)], total: 1 }) });
    const user = userEvent.setup();
    wrap(<TasksPage />);
    expect(await screen.findByText("Task 5")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "My jobs" })).toHaveAttribute("aria-pressed", "true");
    expect(calls.find((c) => c.path === "/worker/complaints").query).toMatchObject({ status: "IN_PROGRESS", assignedToMe: "true", page: "1" });
    await user.click(screen.getByRole("button", { name: "Resolved" }));
    expect(await screen.findByText("Task 8")).toBeInTheDocument();
    expect(calls.at(-1).query).toMatchObject({ status: "RESOLVED" });
    expect(calls.at(-1).query.assignedToMe).toBeUndefined();
  });

  it("falls back to New for an unknown filter and shows an empty message", async () => {
    search = "filter=bogus";
    backend({ "GET /worker/complaints": ok({ items: [], total: 0 }) });
    wrap(<TasksPage />);
    expect(await screen.findByText("No new reports")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New" })).toHaveAttribute("aria-pressed", "true");
  });

  it("loads the next page with Show more", async () => {
    backend({
      "GET /worker/complaints": (q) =>
        q.page === "1"
          ? ok({ items: Array.from({ length: 10 }, (_, i) => task(i + 1)), total: 12 })
          : ok({ items: [task(11), task(12)], total: 12 }),
    });
    const user = userEvent.setup();
    wrap(<TasksPage />);
    expect(await screen.findByText("Showing 10 of 12")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show more" }));
    expect(await screen.findByText("Showing 12 of 12")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
  });
});

describe("task detail: start work", () => {
  it("shows the reported photo with its verified location and starts the job", async () => {
    backend({
      "GET /worker/complaints/c1": ok(detail()),
      "PATCH /worker/complaints/c1/status": () => ok(detail({ status: "IN_PROGRESS", assignedWorker: { id: "w1", name: "Ravi Kumar" } })),
    });
    const user = userEvent.setup();
    wrap(<TaskDetailPage />);
    expect(await screen.findByRole("heading", { name: "Task 1" })).toBeInTheDocument();
    expect(screen.getByTestId("geotag-badge")).toHaveTextContent("Location verified");
    expect(screen.getByText("Tina")).toBeInTheDocument();
    expect(screen.getByTestId("map-center")).toHaveTextContent("19.1867,73.192");
    expect(screen.queryByRole("form", { name: "Mark as resolved" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Start work" }));
    expect(await screen.findByRole("form", { name: "Mark as resolved" })).toBeInTheDocument();
    const patch = calls.find((c) => c.method === "PATCH");
    expect(JSON.parse(patch.body)).toEqual({ status: "IN_PROGRESS" });
    expect(screen.queryByRole("button", { name: "Start work" })).toBeNull();
  });

  it("shows the server message when someone else took the job first", async () => {
    backend({
      "GET /worker/complaints/c1": ok(detail()),
      "PATCH /worker/complaints/c1/status": [409, { success: false, message: "This complaint was just updated by someone else. Please refresh and try again", errors: [] }],
    });
    const user = userEvent.setup();
    wrap(<TaskDetailPage />);
    await user.click(await screen.findByRole("button", { name: "Start work" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("just updated by someone else");
  });

  it("calls an anonymous reporter Anonymous and a missing job not found", async () => {
    backend({ "GET /worker/complaints/c1": ok(detail({ reporter: null })) });
    wrap(<TaskDetailPage />);
    expect(await screen.findByText("Anonymous")).toBeInTheDocument();
  });

  it("explains a job from another department", async () => {
    backend({ "GET /worker/complaints/c1": [404, { success: false, message: "Complaint not found", errors: [] }] });
    wrap(<TaskDetailPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not find this complaint in your department");
  });
});

describe("task detail: resolve with a geotagged photo", () => {
  const inProgress = () => detail({ status: "IN_PROGRESS", assignedWorker: { id: "w1", name: "Ravi Kumar" } });

  it("blocks a photo with no GPS and sends nothing", async () => {
    backend({ "GET /worker/complaints/c1": ok(inProgress()) });
    const user = userEvent.setup();
    wrap(<TaskDetailPage />);
    await user.upload(await screen.findByLabelText(/After-fix photo/), noGpsPhoto());
    expect(await screen.findByTestId("resolve-photo-problem")).toHaveTextContent("no GPS location");
    await user.click(screen.getByRole("button", { name: "Mark as resolved" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no GPS location");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("blocks a photo taken far away and says how far", async () => {
    backend({ "GET /worker/complaints/c1": ok(inProgress()) });
    const user = userEvent.setup();
    wrap(<TaskDetailPage />);
    await user.upload(await screen.findByLabelText(/After-fix photo/), southWestPhoto());
    expect(await screen.findByTestId("resolve-photo-problem")).toHaveTextContent(/taken [\d.]+ (m|km) from the reported location/);
    await user.click(screen.getByRole("button", { name: "Mark as resolved" }));
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("asks for a photo before anything else", async () => {
    backend({ "GET /worker/complaints/c1": ok(inProgress()) });
    const user = userEvent.setup();
    wrap(<TaskDetailPage />);
    await user.click(await screen.findByRole("button", { name: "Mark as resolved" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Add the after-fix photo first");
  });

  it("sends the photo and note as multipart and shows the finished job with its photo", async () => {
    backend({
      "GET /worker/complaints/c1": ok(inProgress()),
      "POST /worker/complaints/c1/resolve": () => ok(detail({ status: "RESOLVED", resolvedAt: new Date().toISOString(), resolutionPhotoUrl: "/uploads/resolutions/x.jpg" })),
    });
    const user = userEvent.setup();
    wrap(<TaskDetailPage />);
    await user.upload(await screen.findByLabelText(/After-fix photo/), gpsPhoto());
    expect(await screen.findByTestId("resolve-gps-ok")).toHaveTextContent("Photo taken 0 m from the reported location");
    await user.type(screen.getByLabelText(/Note for the citizen/), "Filled with asphalt");
    await user.click(screen.getByRole("button", { name: "Mark as resolved" }));
    expect(await screen.findByText("This job is finished. The citizen has been told.")).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST");
    expect(post.body).toBeInstanceOf(FormData);
    expect(post.body.get("photo").name).toBe("at-the-spot.jpg");
    expect(post.body.get("note")).toBe("Filled with asphalt");
    expect(screen.getByAltText("After-fix photo")).toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "Mark as resolved" })).toBeNull();
  });

  it("shows the server's photo message when the backend refuses", async () => {
    backend({
      "GET /worker/complaints/c1": ok(inProgress()),
      "POST /worker/complaints/c1/resolve": [422, { success: false, message: "Validation failed", errors: [{ field: "photo", message: "This photo was taken 900 m from the reported location." }] }],
    });
    const user = userEvent.setup();
    wrap(<TaskDetailPage />);
    await user.upload(await screen.findByLabelText(/After-fix photo/), gpsPhoto());
    await user.click(screen.getByRole("button", { name: "Mark as resolved" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("900 m from the reported location");
    expect(screen.getByRole("form", { name: "Mark as resolved" })).toBeInTheDocument();
  });

  it("a resolved job has no actions", async () => {
    backend({ "GET /worker/complaints/c1": ok(detail({ status: "RESOLVED", resolutionPhotoUrl: "/uploads/resolutions/x.jpg", resolvedAt: new Date().toISOString() })) });
    wrap(<TaskDetailPage />);
    expect(await screen.findByText("This job is finished. The citizen has been told.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start work" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Mark as resolved" })).toBeNull();
  });
});
