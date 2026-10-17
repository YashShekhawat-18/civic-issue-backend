import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/admin/manage/workers",
  useSearchParams: () => new URLSearchParams(""),
}));

import { AuthProvider } from "@/context/AuthContext";
import DepartmentsPage from "@/app/admin/manage/departments/page";
import CategoriesPage from "@/app/admin/manage/categories/page";
import WorkersPage from "@/app/admin/manage/workers/page";
import AuditPage from "@/app/admin/manage/audit/page";
import ManageNav from "@/components/ManageNav";
import { suggestCode, validateCatalog, validateWorker, changedFields, describeAudit } from "@/lib/manage";

const ADMIN = { id: "a1", name: "Sana Admin", email: "a@e.co", role: "ADMIN" };
const ok = (data) => [200, { success: true, data }];
let calls;
function backend(routes) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn(async (url, opts = {}) => {
    const u = new URL(url);
    const path = u.pathname.replace("/api/v1", "");
    const method = opts.method || "GET";
    calls.push({ method, path, query: Object.fromEntries(u.searchParams), body: opts.body ? JSON.parse(opts.body) : undefined });
    const key = `${method} ${path}`;
    const handler = routes[key] ?? (key === "GET /auth/me" ? ok(ADMIN) : null);
    if (!handler) throw new Error("unmocked " + key);
    const [status, body] = typeof handler === "function" ? handler(opts) : handler;
    return { ok: status < 400, status, json: async () => body };
  }));
}
const wrap = (ui) => render(<AuthProvider>{ui}</AuthProvider>);
const dept = (n, over = {}) => ({ id: `d${n}`, name: `Dept ${n}`, code: `D${n}`, description: "", isActive: true, ...over });
const cat = (n, over = {}) => ({ id: `k${n}`, name: `Cat ${n}`, code: `K${n}`, description: "", isActive: true, department: dept(1), ...over });
const worker = (n, over = {}) => ({ id: `w${n}`, name: `Worker ${n}`, email: `w${n}@e.co`, phone: null, departmentId: "d1", department: { id: "d1", name: "Dept 1" }, isActive: true, ...over });
const fail = (status, message, errors = []) => [status, { success: false, message, errors }];

beforeEach(() => vi.unstubAllGlobals());

describe("manage helpers", () => {
  it("suggests an uppercase code from a name", () => {
    expect(suggestCode("Street Lighting")).toBe("STREET_LIGHTING");
    expect(suggestCode("  Water & Sewer! ")).toBe("WATER_SEWER");
    expect(suggestCode("x".repeat(50))).toHaveLength(30);
  });
  it("validates catalog forms like the backend", () => {
    expect(validateCatalog({ name: "A", code: "ok", description: "" })).toHaveProperty("name");
    expect(validateCatalog({ name: "Roads", code: "bad code", description: "" })).toHaveProperty("code");
    expect(validateCatalog({ name: "Roads", code: "road_1", description: "" })).toEqual({});
    expect(validateCatalog({ name: "Pothole", code: "POT", description: "", departmentId: "" }, { needsDepartment: true })).toHaveProperty("departmentId");
  });
  it("validates workers: password only required when creating", () => {
    const base = { name: "Ravi", email: "r@e.co", password: "", phone: "", departmentId: "d1" };
    expect(validateWorker(base, { creating: true })).toHaveProperty("password");
    expect(validateWorker(base, { creating: false })).toEqual({});
    expect(validateWorker({ ...base, password: "abcdefgh" }, { creating: false })).toHaveProperty("password");
    expect(validateWorker({ ...base, phone: "12" }, { creating: false })).toHaveProperty("phone");
    expect(validateWorker({ ...base, email: "nope", password: "abc12345" }, { creating: true })).toHaveProperty("email");
  });
  it("changedFields keeps only what changed", () => {
    expect(changedFields({ a: 1, b: 2 }, { a: 1, b: 3 })).toEqual({ b: 3 });
  });
  it("describes audit entries in plain words", () => {
    const status = describeAudit({ action: "STATUS_CHANGED", metadata: { complaintNumber: "CIV-1", from: "SUBMITTED", to: "IN_PROGRESS", byRole: "ADMIN" } });
    expect(status.title).toBe("CIV-1: Reported to Being fixed");
    expect(status.detail).toBe("Changed by a admin");
    expect(describeAudit({ action: "WORKER_UPDATED", metadata: { fields: ["departmentId"], passwordReset: true } }).detail).toBe("Changed: department. Password was reset");
    expect(describeAudit({ action: "SOMETHING_NEW", metadata: {} }).title).toBe("SOMETHING_NEW");
  });
});

describe("manage navigation", () => {
  it("shows four tabs and marks the current one", () => {
    render(<ManageNav />);
    expect(screen.getByRole("link", { name: "Workers" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Activity log" })).toHaveAttribute("href", "/admin/manage/audit");
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });
});

describe("departments page", () => {
  it("adds a department; the code follows the name", async () => {
    let list = [dept(1)];
    backend({
      "GET /admin/departments": () => ok(list),
      "POST /departments": (opts) => { const b = JSON.parse(opts.body); list = [...list, dept(2, b)]; return [201, { success: true, data: b }]; },
    });
    wrap(<DepartmentsPage />);
    await screen.findByText("Dept 1");
    await userEvent.click(screen.getByRole("button", { name: "Add department" }));
    await userEvent.type(screen.getByLabelText("Name"), "Street Lighting");
    expect(screen.getByLabelText("Code")).toHaveValue("STREET_LIGHTING");
    await userEvent.click(screen.getByRole("button", { name: "Add department" }));
    expect(await screen.findByText("Street Lighting added.")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST").body).toEqual({ name: "Street Lighting", code: "STREET_LIGHTING", description: "" });
    expect(await screen.findByText("Street Lighting")).toBeInTheDocument();
  });

  it("shows validation errors without calling the API", async () => {
    backend({ "GET /admin/departments": ok([]) });
    wrap(<DepartmentsPage />);
    await screen.findByText("No departments yet");
    await userEvent.click(screen.getByRole("button", { name: "Add department" }));
    await userEvent.click(screen.getByRole("button", { name: "Add department" }));
    expect(await screen.findByText("Name must be at least 2 characters")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("edit sends only the changed field", async () => {
    backend({ "GET /admin/departments": ok([dept(1)]), "PATCH /departments/d1": ok({}) });
    wrap(<DepartmentsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit Dept 1" }));
    const desc = screen.getByLabelText("Description (optional)");
    await userEvent.type(desc, "Roads and bridges");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await screen.findByText("Dept 1 updated.");
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ description: "Roads and bridges" });
  });

  it("editing without changes says so and sends nothing", async () => {
    backend({ "GET /admin/departments": ok([dept(1)]) });
    wrap(<DepartmentsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit Dept 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Nothing was changed.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "PATCH")).toBe(false);
  });

  it("deactivating asks first, and shows the backend's reason when it refuses", async () => {
    backend({
      "GET /admin/departments": ok([dept(1)]),
      "PATCH /departments/d1": fail(409, "This department still has active workers. Move or deactivate them first"),
    });
    wrap(<DepartmentsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Deactivate" }));
    expect(calls.some((c) => c.method === "PATCH")).toBe(false); // nothing sent before the confirmation
    await userEvent.click(screen.getByRole("button", { name: "Yes, deactivate Dept 1" }));
    expect(await screen.findByText(/still has active workers/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ isActive: false });
  });

  it("inactive departments can be reactivated", async () => {
    backend({ "GET /admin/departments": ok([dept(1, { isActive: false })]), "PATCH /departments/d1": ok({}) });
    wrap(<DepartmentsPage />);
    expect(await screen.findByText("Inactive")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reactivate" }));
    await screen.findByText("Dept 1 reactivated.");
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ isActive: true });
  });
});

describe("categories page", () => {
  it("adds a category with a department", async () => {
    backend({
      "GET /admin/categories": ok([cat(1)]),
      "GET /admin/departments": ok([dept(1), dept(2, { isActive: false })]),
      "POST /categories": [201, { success: true, data: {} }],
    });
    wrap(<CategoriesPage />);
    await screen.findByText("Cat 1");
    await userEvent.click(await screen.findByRole("button", { name: "Add category" }));
    await userEvent.type(screen.getByLabelText("Name"), "Broken Bench");
    await userEvent.click(screen.getByRole("button", { name: "Add category" }));
    expect(await screen.findByText("Choose a department")).toBeInTheDocument(); // asked before sending
    expect(screen.queryByRole("option", { name: "Dept 2" })).not.toBeInTheDocument(); // inactive departments are not offered
    await userEvent.selectOptions(screen.getByLabelText("Department"), "d1");
    await userEvent.click(screen.getByRole("button", { name: "Add category" }));
    await screen.findByText("Broken Bench added.");
    expect(calls.find((c) => c.method === "POST").body).toEqual({ name: "Broken Bench", code: "BROKEN_BENCH", description: "", departmentId: "d1" });
  });

  it("shows which department receives each category", async () => {
    backend({ "GET /admin/categories": ok([cat(1)]), "GET /admin/departments": ok([dept(1)]) });
    wrap(<CategoriesPage />);
    expect(await screen.findByText(/Goes to Dept 1/)).toBeInTheDocument();
  });

  it("shows a duplicate error from the backend on the form", async () => {
    backend({
      "GET /admin/categories": ok([]),
      "GET /admin/departments": ok([dept(1)]),
      "POST /categories": fail(409, "A category with this name or code already exists"),
    });
    wrap(<CategoriesPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Add category" }));
    await userEvent.type(screen.getByLabelText("Name"), "Pothole");
    await userEvent.selectOptions(screen.getByLabelText("Department"), "d1");
    await userEvent.click(screen.getByRole("button", { name: "Add category" }));
    expect(await screen.findByText("A category with this name or code already exists")).toBeInTheDocument();
  });
});

describe("workers page", () => {
  it("lists workers and filters by department and status", async () => {
    backend({ "GET /admin/workers": ok({ items: [worker(1)], page: 1, limit: 20, total: 1 }), "GET /admin/departments": ok([dept(1), dept(2)]) });
    wrap(<WorkersPage />);
    expect(await screen.findByText("Worker 1")).toBeInTheDocument();
    await screen.findByRole("option", { name: "Dept 2" });
    await userEvent.selectOptions(screen.getByLabelText("Department"), "d2");
    await userEvent.selectOptions(screen.getByLabelText("Status"), "false");
    await waitFor(() => {
      const last = calls.filter((c) => c.path === "/admin/workers").at(-1);
      expect(last.query).toMatchObject({ departmentId: "d2", isActive: "false", page: "1" });
    });
  });

  it("adds a worker with the right body (no phone when empty)", async () => {
    backend({
      "GET /admin/workers": ok({ items: [], page: 1, limit: 20, total: 0 }),
      "GET /admin/departments": ok([dept(1)]),
      "POST /admin/workers": [201, { success: true, data: {} }],
    });
    wrap(<WorkersPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Add worker" }));
    await userEvent.type(screen.getByLabelText("Name"), "Ravi Kumar");
    await userEvent.type(screen.getByLabelText("Email"), "Ravi@Example.com");
    await userEvent.type(screen.getByLabelText("Password"), "Worker12345");
    await userEvent.selectOptions(screen.getByLabelText("Department"), "d1");
    await userEvent.click(screen.getByRole("button", { name: "Add worker" }));
    expect(await screen.findByText(/Ravi Kumar can now log in/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST").body).toEqual({ name: "Ravi Kumar", email: "Ravi@Example.com", password: "Worker12345", departmentId: "d1" });
  });

  it("puts a backend field error (email taken) on the form", async () => {
    backend({
      "GET /admin/workers": ok({ items: [], page: 1, limit: 20, total: 0 }),
      "GET /admin/departments": ok([dept(1)]),
      "POST /admin/workers": fail(409, "This email is already registered"),
    });
    wrap(<WorkersPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Add worker" }));
    await userEvent.type(screen.getByLabelText("Name"), "Ravi Kumar");
    await userEvent.type(screen.getByLabelText("Email"), "ravi@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "Worker12345");
    await userEvent.selectOptions(screen.getByLabelText("Department"), "d1");
    await userEvent.click(screen.getByRole("button", { name: "Add worker" }));
    expect(await screen.findByText("This email is already registered")).toBeInTheDocument();
  });

  it("edit: move department and reset password; an empty phone removes the number", async () => {
    backend({
      "GET /admin/workers": ok({ items: [worker(1, { phone: "9876543210" })], page: 1, limit: 20, total: 1 }),
      "GET /admin/departments": ok([dept(1), dept(2)]),
      "PATCH /admin/workers/w1": ok({}),
    });
    wrap(<WorkersPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit Worker 1" }));
    await screen.findByRole("form", { name: "Edit worker" });
    await userEvent.selectOptions(within_form("Edit worker", "Department"), "d2");
    await userEvent.clear(screen.getByLabelText("Phone (optional)"));
    await userEvent.type(screen.getByLabelText(/New password/), "Fresh12345");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Worker 1 updated and password reset.")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ departmentId: "d2", phone: null, password: "Fresh12345" });
  });

  it("deactivate asks first, then sends isActive false", async () => {
    backend({
      "GET /admin/workers": ok({ items: [worker(1)], page: 1, limit: 20, total: 1 }),
      "GET /admin/departments": ok([dept(1)]),
      "PATCH /admin/workers/w1": ok({}),
    });
    wrap(<WorkersPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Deactivate" }));
    expect(calls.some((c) => c.method === "PATCH")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Yes, deactivate Worker 1" }));
    expect(await screen.findByText("Worker 1 can no longer log in.")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ isActive: false });
  });

  it("paginates", async () => {
    backend({
      "GET /admin/workers": (o) => ok({ items: [worker(1)], page: 1, limit: 20, total: 45 }),
      "GET /admin/departments": ok([dept(1)]),
    });
    wrap(<WorkersPage />);
    await screen.findByText("Page 1 of 3 (45 in all)");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(calls.filter((c) => c.path === "/admin/workers").at(-1).query.page).toBe("2"));
  });
});

function within_form(name, label) {
  const form = screen.getByRole("form", { name });
  return form.querySelector(`select[name="departmentId"]`) ?? screen.getByLabelText(label);
}

describe("audit page", () => {
  const entry = (n, over = {}) => ({
    id: `e${n}`, action: "STATUS_CHANGED", entity: "COMPLAINT", entityId: "c1",
    user: { id: "a1", name: "Sana Admin", role: "ADMIN" }, createdAt: "2026-10-17T10:00:00Z",
    metadata: { complaintNumber: `CIV-${n}`, from: "SUBMITTED", to: "IN_PROGRESS", byRole: "ADMIN" }, ...over,
  });

  it("shows entries in plain words with who and when", async () => {
    backend({ "GET /admin/audit-logs": ok({ items: [entry(1), entry(2, { action: "WORKER_CREATED", entity: "USER", metadata: { name: "Ravi", departmentCode: "ROAD" } })], page: 1, limit: 20, total: 2 }) });
    wrap(<AuditPage />);
    expect(await screen.findByText("CIV-1: Reported to Being fixed")).toBeInTheDocument();
    expect(screen.getByText("Worker added: Ravi")).toBeInTheDocument();
    expect(screen.getByTestId("audit-count")).toHaveTextContent("2 entries");
    expect(screen.getAllByText(/Sana Admin \(admin\)/)).toHaveLength(2);
  });

  it("filters by what happened and by subject, back on page 1", async () => {
    backend({ "GET /admin/audit-logs": ok({ items: [entry(1)], page: 1, limit: 20, total: 1 }) });
    wrap(<AuditPage />);
    await screen.findByText("CIV-1: Reported to Being fixed");
    await userEvent.selectOptions(screen.getByLabelText("What happened"), "WORKER_CREATED");
    await userEvent.selectOptions(screen.getByLabelText("About"), "USER");
    await waitFor(() => expect(calls.filter((c) => c.path === "/admin/audit-logs").at(-1).query).toMatchObject({ action: "WORKER_CREATED", entity: "USER", page: "1" }));
  });

  it("has an empty state", async () => {
    backend({ "GET /admin/audit-logs": ok({ items: [], page: 1, limit: 20, total: 0 }) });
    wrap(<AuditPage />);
    expect(await screen.findByText("Nothing logged yet")).toBeInTheDocument();
  });

  it("copes with a deleted actor", async () => {
    backend({ "GET /admin/audit-logs": ok({ items: [entry(1, { user: null })], page: 1, limit: 20, total: 1 }) });
    wrap(<AuditPage />);
    expect(await screen.findByText(/Unknown user/)).toBeInTheDocument();
  });
});
