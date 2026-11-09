"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";

export function useApiData<T>(path: string | null, initial: T | null = null) {
  const [data, setData] = useState<T | null>(initial);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api<T>(path));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, loading, error, reload, setData };
}

export function useCountdown(target: string | null | undefined, tickMs = 1000) {
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    if (!target) {
      setRemaining(0);
      return;
    }
    const compute = () => {
      const ms = new Date(target).getTime() - Date.now();
      setRemaining(Math.max(0, Math.floor(ms / 1000)));
    };
    compute();
    const timer = window.setInterval(compute, tickMs);
    return () => window.clearInterval(timer);
  }, [target, tickMs]);
  return remaining;
}
