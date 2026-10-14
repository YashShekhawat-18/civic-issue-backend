"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, setUnauthorizedHandler } from "@/lib/api";
import { clearToken, getToken, setToken } from "@/lib/storage";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true until we know if a session exists

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  // On first load: if a token is stored, ask the backend who it belongs to.
  useEffect(() => {
    let cancelled = false;
    async function restore() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.get("/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) clearToken(); // expired / invalid token
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  // Any 401 from any request logs the user out.
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const login = useCallback(async (email, password) => {
    const result = await api.post("/auth/login", { email: email.trim().toLowerCase(), password }, { auth: false });
    setToken(result.accessToken);
    setUser(result.user);
    return result.user;
  }, []);

  const register = useCallback(async ({ name, email, password, phone }) => {
    const body = { name: name.trim(), email: email.trim().toLowerCase(), password };
    if (phone && phone.trim()) body.phone = phone.trim();
    await api.post("/auth/register", body, { auth: false });
  }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
