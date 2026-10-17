"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * useApi("/gamification/me") -> { data, error, loading, reload }
 * Fetches when the page opens (and again when path/params/refreshKey change or reload() is called).
 * During reload() the previous data stays in place (loading is true). Pass a falsy path to wait (nothing is fetched and loading stays false).
 */
export function useApi(path, params, refreshKey = "") {
  const paramsKey = JSON.stringify(params ?? {});
  const [version, setVersion] = useState(0);
  const baseKey = `${path}|${paramsKey}|${refreshKey}`;
  const requestKey = `${baseKey}|${version}`;
  const [result, setResult] = useState({ key: null, base: null, data: null, error: "" });

  useEffect(() => {
    if (!path) return undefined;
    let cancelled = false;
    api
      .get(path, JSON.parse(paramsKey))
      .then((data) => !cancelled && setResult({ key: requestKey, base: baseKey, data, error: "" }))
      .catch((err) => !cancelled && setResult({ key: requestKey, base: baseKey, data: null, error: err.message }));
    return () => {
      cancelled = true;
    };
  }, [path, paramsKey, requestKey, baseKey]);

  const idle = !path;
  const loading = !idle && result.key !== requestKey;
  const ready = !idle && !loading;
  // While reload() is running for the same request, keep showing the last data so the page does not flash.
  const keepOld = loading && result.base === baseKey;
  return {
    data: ready || keepOld ? result.data : null,
    error: ready ? result.error : "",
    loading,
    reload: () => setVersion((v) => v + 1),
  };
}
