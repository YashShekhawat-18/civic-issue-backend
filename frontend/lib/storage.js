import { TOKEN_KEY } from "./config";

// localStorage can throw (private mode, blocked cookies) or be missing on the server,
// so every access is wrapped. Trade-off to explain in the viva: localStorage is readable
// by any script on the page (XSS risk); httpOnly cookies avoid that but need extra backend work.
export function getToken() {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore */
  }
}

export function clearToken() {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}
