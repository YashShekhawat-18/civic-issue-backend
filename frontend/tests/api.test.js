import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, setUnauthorizedHandler } from "@/lib/api";
import { setToken } from "@/lib/storage";

function mockFetch(status, body) {
  const fn = vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => setUnauthorizedHandler(null));
afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("returns data from the success envelope", async () => {
    mockFetch(200, { success: true, message: "ok", data: { a: 1 } });
    await expect(api.get("/x")).resolves.toEqual({ a: 1 });
  });

  it("sends Bearer token and JSON body", async () => {
    setToken("tok123");
    const fn = mockFetch(200, { success: true, data: null });
    await api.post("/x", { hello: "w" });
    const [url, opts] = fn.mock.calls[0];
    expect(url).toMatch(/\/x$/);
    expect(opts.headers.Authorization).toBe("Bearer tok123");
    expect(opts.headers["Content-Type"]).toBe("application/json");
    expect(opts.body).toBe('{"hello":"w"}');
  });

  it("omits the token when auth:false", async () => {
    setToken("tok123");
    const fn = mockFetch(200, { success: true, data: null });
    await api.post("/auth/login", {}, { auth: false });
    expect(fn.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("builds query strings and skips empty values", async () => {
    const fn = mockFetch(200, { success: true, data: [] });
    await api.get("/c", { status: "OPEN", page: 2, q: "", x: undefined });
    const url = fn.mock.calls[0][0];
    expect(url).toContain("status=OPEN");
    expect(url).toContain("page=2");
    expect(url).not.toContain("q=");
    expect(url).not.toContain("x=");
  });

  it("does not set Content-Type for FormData uploads", async () => {
    const fn = mockFetch(200, { success: true, data: null });
    await api.post("/up", new FormData());
    expect(fn.mock.calls[0][1].headers["Content-Type"]).toBeUndefined();
  });

  it("throws ApiError with message and field errors", async () => {
    mockFetch(422, { success: false, message: "Validation failed", errors: [{ field: "email", message: "bad" }] });
    const err = await api.post("/x", {}).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.errors[0].field).toBe("email");
  });

  it("friendly message on 429 and on network failure", async () => {
    mockFetch(429, { success: false, message: "x" });
    expect((await api.get("/x").catch((e) => e)).message).toMatch(/Too many/);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fail")));
    const err = await api.get("/x").catch((e) => e);
    expect(err.status).toBe(0);
    expect(err.message).toMatch(/Cannot reach/);
  });

  it("calls the unauthorized handler on 401 only when a token was sent", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    mockFetch(401, { success: false, message: "Invalid email or password" });
    await api.post("/auth/login", {}, { auth: false }).catch(() => {});
    expect(handler).not.toHaveBeenCalled();
    setToken("t");
    await api.get("/auth/me").catch(() => {});
    expect(handler).toHaveBeenCalledTimes(1);
  });
});
