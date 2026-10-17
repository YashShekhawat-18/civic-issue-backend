import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));
// The real map needs a browser with layout; replace it with a button that "picks" a point.
vi.mock("@/components/LocationPickerLoader", () => ({
  default: ({ value, onChange, error }) => (
    <div>
      <button type="button" onClick={() => onChange({ lat: 19.0760, lng: 72.8777 })}>pick-point</button>
      <span data-testid="picked">{value ? `${value.lat},${value.lng}` : "none"}</span>
      {error && <span>{error}</span>}
    </div>
  ),
}));

import ReportPage from "@/app/citizen/report/page";
import { gpsPhoto, noGpsPhoto } from "./photos";

const CATS = [{ id: "c1", name: "Pothole" }, { id: "c2", name: "Garbage" }];
let calls;
function backend(postResult) {
  calls = [];
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: () => "blob:x", revokeObjectURL: () => {} }));
  vi.stubGlobal("fetch", vi.fn(async (url, opts = {}) => {
    const path = new URL(url).pathname.replace("/api/v1", "");
    calls.push({ method: opts.method || "GET", path, body: opts.body });
    if (path === "/categories") return { ok: true, status: 200, json: async () => ({ success: true, data: CATS }) };
    const hit = postResult[`${opts.method} ${path}`];
    if (!hit) throw new Error("unmocked " + path);
    return { ok: hit[0] < 400, status: hit[0], json: async () => hit[1] };
  }));
}

async function fillValid(user) {
  await screen.findByRole("option", { name: "Pothole" });
  await user.selectOptions(screen.getByLabelText("Category"), "c1");
  await user.type(screen.getByLabelText("Title"), "Big pothole");
  await user.type(screen.getByLabelText("Description"), "Deep pothole near the bus stop");
  await user.upload(screen.getByLabelText(/Photo/), gpsPhoto());
  // the photo carries its position, so the pin is placed automatically
  await waitFor(() => expect(screen.getByTestId("picked")).toHaveTextContent("19.1867,73.192"));
}

beforeEach(() => window.localStorage.setItem("civic_access_token", "T"));

describe("report page", () => {
  it("loads categories into the dropdown", async () => {
    backend({});
    render(<ReportPage />);
    expect(await screen.findByRole("option", { name: "Garbage" })).toBeInTheDocument();
  });

  it("blocks an empty submit with errors and sends nothing", async () => {
    backend({});
    render(<ReportPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Submit complaint" }));
    expect(await screen.findByText("Choose a category")).toBeInTheDocument();
    expect(screen.getByText("Please add a photo of the issue")).toBeInTheDocument();
    expect(screen.getByText("Pick the location on the map")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("submits multipart data and shows the complaint number", async () => {
    backend({ "POST /complaints": [201, { success: true, data: { complaintNumber: "CIV-2026-000007", department: { name: "Roads" } } }] });
    const user = userEvent.setup();
    render(<ReportPage />);
    await fillValid(user);
    await user.click(screen.getByRole("button", { name: "Submit complaint" }));
    expect(await screen.findByTestId("complaint-number")).toHaveTextContent("CIV-2026-000007");
    const post = calls.find((c) => c.method === "POST");
    expect(post.body).toBeInstanceOf(FormData);
    expect(post.body.get("latitude")).toBe("19.1867");
    expect(post.body.get("longitude")).toBe("73.192");
    expect(post.body.get("categoryId")).toBe("c1");
    expect(post.body.get("photo").name).toBe("at-the-spot.jpg");
  });

  it("tells the citizen the pin came from the photo", async () => {
    backend({});
    const user = userEvent.setup();
    render(<ReportPage />);
    await fillValid(user);
    expect(screen.getByTestId("photo-gps-ok")).toHaveTextContent("Location found in the photo");
  });

  it("rejects a photo without GPS before anything is sent", async () => {
    backend({});
    const user = userEvent.setup();
    render(<ReportPage />);
    await screen.findByRole("option", { name: "Pothole" });
    await user.upload(screen.getByLabelText(/Photo/), noGpsPhoto());
    expect(await screen.findByTestId("photo-problem")).toHaveTextContent("no GPS location");
    await user.selectOptions(screen.getByLabelText("Category"), "c1");
    await user.type(screen.getByLabelText("Title"), "Big pothole");
    await user.type(screen.getByLabelText("Description"), "Deep pothole near the bus stop");
    await user.click(screen.getByText("pick-point"));
    await user.click(screen.getByRole("button", { name: "Submit complaint" }));
    expect(screen.getByTestId("photo-problem")).toHaveTextContent("no GPS location");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("tells the citizen at once when the file is a PNG", async () => {
    backend({});
    const user = userEvent.setup({ applyAccept: false }); // the file picker would hide a PNG; a drag-and-drop would not
    render(<ReportPage />);
    await screen.findByRole("option", { name: "Pothole" });
    await user.upload(screen.getByLabelText(/Photo/), new File([new Uint8Array(20)], "shot.png", { type: "image/png" }));
    expect(await screen.findByTestId("photo-problem")).toHaveTextContent(/JPEG.*location/);
  });

  it("rejects a photo taken far from the pin and says how far", async () => {
    backend({});
    const user = userEvent.setup();
    render(<ReportPage />);
    await fillValid(user);
    await user.click(screen.getByText("pick-point")); // moves the pin about 150 km away
    expect(await screen.findByTestId("photo-problem")).toHaveTextContent(/taken [\d.]+ (m|km) from the pinned location/);
    await user.click(screen.getByRole("button", { name: "Submit complaint" }));
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("shows the duplicate warning and lets the citizen upvote", async () => {
    const existing = { id: "e1", title: "Pothole on MG Road", complaintNumber: "CIV-2026-000001", status: "OPEN", upvoteCount: 2, hasUpvoted: false, isOwnComplaint: false, distanceMeters: 30, photoUrl: "/uploads/a.jpg" };
    backend({
      "POST /complaints": [200, { success: true, data: { duplicate: true, message: "A similar complaint already exists nearby.", existingComplaint: existing, canUpvote: true } }],
      "POST /complaints/e1/upvote": [201, { success: true, data: { upvoteCount: 3, hasUpvoted: true } }],
    });
    const user = userEvent.setup();
    render(<ReportPage />);
    await fillValid(user);
    await user.click(screen.getByRole("button", { name: "Submit complaint" }));
    expect(await screen.findByText("This issue may already be reported")).toBeInTheDocument();
    expect(screen.getByText("Pothole on MG Road")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Upvote this complaint" }));
    await waitFor(() => expect(screen.getByTestId("upvote-count")).toHaveTextContent("3 people have upvoted"));
    expect(screen.queryByRole("button", { name: "Upvote this complaint" })).toBeNull();
  });

  it("own duplicate: no upvote button, can go back to the form", async () => {
    const existing = { id: "e1", title: "Mine", complaintNumber: "CIV-1", status: "OPEN", upvoteCount: 0, hasUpvoted: false, isOwnComplaint: true };
    backend({ "POST /complaints": [200, { success: true, data: { duplicate: true, message: "You have already reported this issue nearby.", existingComplaint: existing, canUpvote: false } }] });
    const user = userEvent.setup();
    render(<ReportPage />);
    await fillValid(user);
    await user.click(screen.getByRole("button", { name: "Submit complaint" }));
    expect(await screen.findByText("You have already reported this issue nearby.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upvote this complaint" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Back to the form" }));
    expect(await screen.findByRole("button", { name: "Submit complaint" })).toBeInTheDocument();
  });

  it("shows server errors without losing the form", async () => {
    backend({ "POST /complaints": [400, { success: false, message: "Only JPEG, PNG or WebP images are allowed", errors: [] }] });
    const user = userEvent.setup();
    render(<ReportPage />);
    await fillValid(user);
    await user.click(screen.getByRole("button", { name: "Submit complaint" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Only JPEG, PNG or WebP");
    expect(screen.getByLabelText("Title")).toHaveValue("Big pothole");
  });
});
