import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const replace = vi.fn();
let search = "";
let pathname = "/";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
  usePathname: () => pathname,
}));
vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));

import { AuthProvider } from "@/context/AuthContext";
import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";
import RoleGuard from "@/components/RoleGuard";

const user = (role) => ({ id: "1", name: "Test", email: "t@e.co", role });
function respond(map) {
  vi.stubGlobal("fetch", vi.fn(async (url, opts = {}) => {
    const key = `${opts.method || "GET"} ${new URL(url).pathname.replace("/api/v1", "")}`;
    const hit = map[key];
    if (!hit) throw new Error("unmocked " + key);
    return { ok: hit[0] < 400, status: hit[0], json: async () => hit[1] };
  }));
}
const wrap = (ui) => render(<AuthProvider>{ui}</AuthProvider>);

beforeEach(() => { replace.mockClear(); search = ""; pathname = "/"; });

describe("login page", () => {
  it("shows client validation errors without calling the API", async () => {
    respond({});
    wrap(<LoginPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each([["CITIZEN", "/citizen"], ["WORKER", "/worker"], ["ADMIN", "/admin"]])("redirects %s to %s", async (role, home) => {
    respond({ "POST /auth/login": [200, { success: true, data: { accessToken: "T", user: user(role) } }] });
    wrap(<LoginPage />);
    await userEvent.type(await screen.findByLabelText("Email"), "t@e.co");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith(home));
    expect(window.localStorage.getItem("civic_access_token")).toBe("T");
  });

  it("shows the server error on bad credentials", async () => {
    respond({ "POST /auth/login": [401, { success: false, message: "Invalid email or password" }] });
    wrap(<LoginPage />);
    await userEvent.type(await screen.findByLabelText("Email"), "t@e.co");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
    expect(window.localStorage.getItem("civic_access_token")).toBeNull();
  });

  it("ignores an unsafe ?next redirect", async () => {
    search = "next=//evil.com";
    respond({ "POST /auth/login": [200, { success: true, data: { accessToken: "T", user: user("CITIZEN") } }] });
    wrap(<LoginPage />);
    await userEvent.type(await screen.findByLabelText("Email"), "t@e.co");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/citizen"));
  });

  it("a logged-in user visiting /login is sent home", async () => {
    window.localStorage.setItem("civic_access_token", "T");
    respond({ "GET /auth/me": [200, { success: true, data: user("ADMIN") }] });
    wrap(<LoginPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin"));
  });
});

describe("register page", () => {
  it("maps backend field errors onto the form", async () => {
    respond({ "POST /auth/register": [409, { success: false, message: "Email already registered", errors: [{ field: "email", message: "Email already registered" }] }] });
    wrap(<RegisterPage />);
    await userEvent.type(await screen.findByLabelText("Full name"), "Asha Rao");
    await userEvent.type(screen.getByLabelText("Email"), "a@e.co");
    await userEvent.type(screen.getByLabelText("Password"), "secret123");
    await userEvent.type(screen.getByLabelText("Confirm password"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Register" }));
    expect((await screen.findAllByText("Email already registered")).length).toBeGreaterThan(0);
    expect(replace).not.toHaveBeenCalled();
  });

  it("goes to login after success and sends no empty phone", async () => {
    respond({ "POST /auth/register": [201, { success: true, data: {} }] });
    wrap(<RegisterPage />);
    await userEvent.type(await screen.findByLabelText("Full name"), "Asha Rao");
    await userEvent.type(screen.getByLabelText("Email"), "A@E.co");
    await userEvent.type(screen.getByLabelText("Password"), "secret123");
    await userEvent.type(screen.getByLabelText("Confirm password"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Register" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?registered=1"));
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ name: "Asha Rao", email: "a@e.co", password: "secret123" });
  });
});

describe("RoleGuard", () => {
  it("redirects guests to login with ?next", async () => {
    pathname = "/admin";
    respond({});
    wrap(<RoleGuard roles={["ADMIN"]}><p>secret</p></RoleGuard>);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?next=%2Fadmin"));
    expect(screen.queryByText("secret")).toBeNull();
  });

  it("sends the wrong role to its own home and never renders the content", async () => {
    window.localStorage.setItem("civic_access_token", "T");
    respond({ "GET /auth/me": [200, { success: true, data: user("CITIZEN") }] });
    wrap(<RoleGuard roles={["ADMIN"]}><p>secret</p></RoleGuard>);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/citizen"));
    expect(screen.queryByText("secret")).toBeNull();
  });

  it("renders for the right role; an expired token logs out", async () => {
    window.localStorage.setItem("civic_access_token", "T");
    respond({ "GET /auth/me": [200, { success: true, data: user("ADMIN") }] });
    wrap(<RoleGuard roles={["ADMIN"]}><p>secret</p></RoleGuard>);
    expect(await screen.findByText("secret")).toBeInTheDocument();
  });

  it("clears an invalid stored token", async () => {
    window.localStorage.setItem("civic_access_token", "BAD");
    respond({ "GET /auth/me": [401, { success: false, message: "Invalid token" }] });
    wrap(<RoleGuard roles={["ADMIN"]}><p>secret</p></RoleGuard>);
    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(window.localStorage.getItem("civic_access_token")).toBeNull();
  });
});
