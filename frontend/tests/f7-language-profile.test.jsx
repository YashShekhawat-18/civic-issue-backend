import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/link", () => ({ default: ({ href, children, ...p }) => <a href={href} {...p}>{children}</a> }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/profile" }));

import { AuthProvider } from "@/context/AuthContext";
import { LanguageProvider } from "@/context/LanguageContext";
import LanguageSwitch from "@/components/LanguageSwitch";
import ProfilePage from "@/app/profile/page";
import { translate } from "@/lib/i18n";
import { timeAgo } from "@/lib/format";
import { profileChanges, validatePasswordChange, validateProfile } from "@/lib/profile";

const USER = { id: "u1", name: "Tina Rao", email: "t@e.co", role: "CITIZEN", points: 1, phone: "+919876543210" };
let calls;
function backend(routes) {
  calls = [];
  vi.stubGlobal("fetch", vi.fn(async (url, opts = {}) => {
    const path = new URL(url).pathname.replace("/api/v1", "");
    const key = `${opts.method || "GET"} ${path}`;
    calls.push({ key, body: opts.body ? JSON.parse(opts.body) : undefined });
    const r = routes[key] ?? (key === "GET /auth/me" ? [200, { success: true, data: USER }] : null);
    if (!r) throw new Error("unmocked " + key);
    return { ok: r[0] < 400, status: r[0], json: async () => r[1] };
  }));
}
const page = () => render(<LanguageProvider><AuthProvider><LanguageSwitch /><ProfilePage /></AuthProvider></LanguageProvider>);
beforeEach(() => window.localStorage.setItem("civic_access_token", "T"));

describe("translate", () => {
  it("returns Hindi, falls back to English, fills placeholders", () => {
    expect(translate("hi", "Home")).toBe("होम");
    expect(translate("en", "Home")).toBe("Home");
    expect(translate("hi", "Some unknown text")).toBe("Some unknown text");
    expect(translate("hi", "Hello, {name}", { name: "Asha" })).toBe("नमस्ते, Asha");
  });
  it("translates the photo distance sentence", () => {
    const en = "This photo was taken 1.2 km from the pinned location. It must be within 300 m. Take the photo at the spot.";
    expect(translate("hi", en)).toContain("1.2 km");
  });
  it("timeAgo follows the language", () => {
    const now = Date.parse("2026-10-15T12:00:00Z");
    expect(timeAgo("2026-10-13T12:00:00Z", now)).toBe("2 days ago");
  });
});

describe("profile rules", () => {
  it("validates", () => {
    expect(validateProfile({ name: "A", phone: "" }).name).toBeTruthy();
    expect(validateProfile({ name: "Asha", phone: "12" }).phone).toBeTruthy();
    expect(validatePasswordChange({ currentPassword: "a1b2c3d4", newPassword: "a1b2c3d4", confirmPassword: "a1b2c3d4" }).newPassword).toBeTruthy();
    expect(validatePasswordChange({ currentPassword: "old12345", newPassword: "New12345", confirmPassword: "x" }).confirmPassword).toBeTruthy();
  });
  it("sends only changes and null for a cleared phone", () => {
    expect(profileChanges({ name: "Tina Rao", phone: "+919876543210" }, USER)).toEqual({});
    expect(profileChanges({ name: "Tina Rao", phone: "" }, USER)).toEqual({ phone: null });
  });
});

describe("profile page", () => {
  it("saves the name", async () => {
    backend({ "PATCH /users/me": [200, { success: true, data: {} }] });
    page();
    const name = await screen.findByLabelText("Name");
    await userEvent.clear(name);
    await userEvent.type(name, "Asha Kumari");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Profile updated")).toBeInTheDocument();
    expect(calls.find((c) => c.key === "PATCH /users/me").body).toEqual({ name: "Asha Kumari" });
  });
  it("changes the password", async () => {
    backend({ "POST /users/me/change-password": [200, { success: true, data: {} }] });
    page();
    await userEvent.type(await screen.findByLabelText("Current password"), "Old12345");
    await userEvent.type(screen.getByLabelText("New password"), "Newer12345");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "Newer12345");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByText("Password changed")).toBeInTheDocument();
    expect(calls.find((c) => c.key.includes("change-password")).body).toEqual({ currentPassword: "Old12345", newPassword: "Newer12345" });
  });
  it("switches to Hindi and remembers it", async () => {
    backend({});
    page();
    await screen.findByLabelText("Name");
    await userEvent.click(screen.getByRole("button", { name: "हिन्दी" }));
    expect(await screen.findByText("मेरी प्रोफ़ाइल")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem("civic_lang")).toBe("hi"));
  });
});
