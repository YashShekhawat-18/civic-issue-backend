import { API_URL } from "./config";
import { getToken } from "./storage";

// Error thrown for every failed request, carrying what the backend said.
export class ApiError extends Error {
  constructor(status, message, errors = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors; // [{field, message}] for validation failures
  }
}

// AuthContext registers a function here so a 401 anywhere logs the user out.
let unauthorizedHandler = null;
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn;
}

function buildUrl(path, params) {
  const url = new URL(`${API_URL}${path.startsWith("/") ? path : `/${path}`}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

/**
 * request("/auth/login", { method: "POST", body: {...} }) -> returns `data` from the
 * backend's {success, message, data} envelope, or throws ApiError.
 * Pass FormData as body for file uploads (the browser sets the multipart header itself).
 */
export async function request(path, { method = "GET", body, params, auth = true, signal } = {}) {
  const headers = {};
  const token = auth ? getToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(buildUrl(path, params), { method, headers, body: payload, signal });
  } catch (err) {
    if (err?.name === "AbortError") throw err;
    throw new ApiError(0, "Cannot reach the server. Check your connection and that the backend is running.");
  }

  let json = null;
  try {
    json = await response.json();
  } catch {
    /* non-JSON body */
  }

  if (!response.ok || json?.success === false) {
    if (response.status === 401 && token && unauthorizedHandler) unauthorizedHandler();
    const message =
      response.status === 429
        ? "Too many requests. Please wait a moment and try again."
        : json?.message || `Request failed (${response.status})`;
    throw new ApiError(response.status, message, json?.errors || []);
  }
  return json?.data ?? null;
}

export const api = {
  get: (path, params, opts) => request(path, { ...opts, params }),
  post: (path, body, opts) => request(path, { ...opts, method: "POST", body }),
  put: (path, body, opts) => request(path, { ...opts, method: "PUT", body }),
  patch: (path, body, opts) => request(path, { ...opts, method: "PATCH", body }),
  delete: (path, opts) => request(path, { ...opts, method: "DELETE" }),
};
